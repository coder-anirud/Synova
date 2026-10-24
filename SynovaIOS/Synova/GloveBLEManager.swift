import CoreBluetooth
import Foundation
import UIKit

final class GloveBLEManager: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate {
    static let shared = GloveBLEManager()

    static let serviceID = CBUUID(string: "8F0C1000-7B24-4C6A-9E45-12DB72D30100")
    private let commandID = CBUUID(string: "8F0C1001-7B24-4C6A-9E45-12DB72D30100")
    private let responseID = CBUUID(string: "8F0C1002-7B24-4C6A-9E45-12DB72D30100")

    var onUpdate: (([String: Any]) -> Void)? {
        didSet { publish() }
    }

    private var central: CBCentralManager?
    private var devices: [UUID: CBPeripheral] = [:]
    private var wantsScan = false
    private var peripheral: CBPeripheral?
    private var commandCharacteristic: CBCharacteristic?
    private var responseCharacteristic: CBCharacteristic?
    private var heartbeat: Timer?
    private var timeout: Timer?
    private var lastPong = Date.distantPast
    private var pending: String?
    private var ready = false
    private var armed = false
    private var stopped = false
    private var lastCommand = "REST"
    private var lastAcknowledgedAt: String?
    private var message = "Connect a glove to begin."

    private override init() {
        super.init()
        NotificationCenter.default.addObserver(self, selector: #selector(appDidEnterBackground), name: UIApplication.didEnterBackgroundNotification, object: nil)
    }

    func handle(_ request: [String: Any]) {
        guard let action = request["action"] as? String else { return }
        switch action {
        case "status": publish()
        case "scan": scan()
        case "connect":
            guard let text = request["id"] as? String, let id = UUID(uuidString: text), let found = devices[id] else {
                message = "Choose a glove from the list first."
                publish()
                return
            }
            central?.stopScan()
            peripheral = found
            message = "Connecting to \(found.name ?? "Synova Glove")…"
            central?.connect(found)
            publish()
        case "disconnect": disconnect()
        case "arm", "disarm", "open", "close", "rest", "stop", "reset": send(action.uppercased())
        default: break
        }
    }

    func publishCurrent() { publish() }

    private func scan() {
        wantsScan = true
        if central == nil { central = CBCentralManager(delegate: self, queue: .main) }
        guard let central, central.state == .poweredOn else {
            message = central?.state == .unsupported ? "Bluetooth is unavailable in Simulator. Use a physical iPhone." : "Starting Bluetooth. Synova will look for the glove when it is ready."
            publish()
            return
        }
        wantsScan = false
        devices.removeAll()
        central.scanForPeripherals(withServices: [Self.serviceID], options: [CBCentralManagerScanOptionAllowDuplicatesKey: false])
        message = "Looking for Synova Glove…"
        publish()
    }

    private func disconnect() {
        if peripheral?.state == .connected { write("STOP") }
        if let peripheral { central?.cancelPeripheralConnection(peripheral) }
        clearConnection("Glove disconnected.")
    }

    private func send(_ command: String) {
        guard peripheral?.state == .connected, ready || command == "STOP" || command == "RESET", commandCharacteristic != nil else {
            message = "Connect a ready glove before sending commands."
            publish()
            return
        }
        guard pending == nil || command == "STOP" else {
            message = "Waiting for the glove to respond."
            publish()
            return
        }
        if command == "ARM" && stopped { message = "Reset the emergency stop first."; publish(); return }
        if ["OPEN", "CLOSE", "REST"].contains(command) && (!armed || stopped) {
            message = "Arm the glove before movement."
            publish()
            return
        }
        if command == "RESET" && !stopped { return }
        if command == "STOP" { armed = false; stopped = true; ready = false }
        pending = command
        write(command)
        timeout?.invalidate()
        timeout = Timer.scheduledTimer(withTimeInterval: 2, repeats: false) { [weak self] _ in
            guard let self, self.pending == command else { return }
            self.message = "No acknowledgment from the glove. Movement is locked."
            if let peripheral = self.peripheral { self.central?.cancelPeripheralConnection(peripheral) }
            self.clearConnection(self.message)
        }
        publish()
    }

    private func write(_ command: String) {
        guard let peripheral, let commandCharacteristic, let data = command.data(using: .utf8) else { return }
        peripheral.writeValue(data, for: commandCharacteristic, type: .withResponse)
    }

    private func clearConnection(_ reason: String) {
        heartbeat?.invalidate(); heartbeat = nil
        timeout?.invalidate(); timeout = nil
        pending = nil
        peripheral = nil
        commandCharacteristic = nil
        responseCharacteristic = nil
        ready = false
        armed = false
        stopped = true
        message = reason
        publish()
    }

    private func publish() {
        onUpdate?([
            "bluetooth": central?.state == .poweredOn ? "ready" : central?.state == .unsupported ? "unsupported" : "unavailable",
            "scanning": central?.isScanning ?? false,
            "devices": devices.values.map { ["id": $0.identifier.uuidString, "name": $0.name ?? "Synova Glove"] },
            "connected": peripheral?.state == .connected,
            "ready": ready,
            "armed": armed,
            "stopped": stopped,
            "command": lastCommand,
            "lastAcknowledgedAt": lastAcknowledgedAt as Any? ?? NSNull(),
            "message": message
        ])
    }

    @objc private func appDidEnterBackground() {
        if peripheral?.state == .connected { write("STOP") }
        armed = false
        stopped = true
        ready = false
        publish()
    }

    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        if central.state != .poweredOn, peripheral != nil { clearConnection("Bluetooth turned off. Movement is locked.") }
        if central.state == .poweredOn && wantsScan { scan(); return }
        if central.state == .unsupported { wantsScan = false; message = "Bluetooth is unavailable in Simulator. Use a physical iPhone." }
        publish()
    }

    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral, advertisementData: [String: Any], rssi RSSI: NSNumber) {
        devices[peripheral.identifier] = peripheral
        publish()
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        peripheral.delegate = self
        message = "Checking glove controls…"
        peripheral.discoverServices([Self.serviceID])
        publish()
    }

    func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral, error: Error?) {
        clearConnection("Could not connect to the glove. \(error?.localizedDescription ?? "Try again.")")
    }

    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        clearConnection("Glove connection lost. The controller must stop on its own watchdog.")
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        guard error == nil, let service = peripheral.services?.first(where: { $0.uuid == Self.serviceID }) else {
            clearConnection("Synova glove service was not found.")
            central?.cancelPeripheralConnection(peripheral)
            return
        }
        peripheral.discoverCharacteristics([commandID, responseID], for: service)
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        guard error == nil else { clearConnection("Could not read glove controls."); central?.cancelPeripheralConnection(peripheral); return }
        commandCharacteristic = service.characteristics?.first(where: { $0.uuid == commandID && $0.properties.contains(.write) })
        responseCharacteristic = service.characteristics?.first(where: { $0.uuid == responseID && $0.properties.contains(.notify) })
        guard commandCharacteristic != nil, let responseCharacteristic else {
            clearConnection("Glove firmware does not match Synova protocol v1.")
            central?.cancelPeripheralConnection(peripheral)
            return
        }
        peripheral.setNotifyValue(true, for: responseCharacteristic)
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic, error: Error?) {
        guard error == nil, characteristic.isNotifying else { clearConnection("Glove responses are unavailable."); central?.cancelPeripheralConnection(peripheral); return }
        write("HELLO")
        timeout = Timer.scheduledTimer(withTimeInterval: 2, repeats: false) { [weak self] _ in
            guard let self, !self.ready else { return }
            self.clearConnection("Glove did not answer the setup check.")
            self.central?.cancelPeripheralConnection(peripheral)
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        guard error == nil, let value = characteristic.value, let line = String(data: value, encoding: .utf8) else { return }
        let reply = line.trimmingCharacters(in: .whitespacesAndNewlines)
        if reply == "ACK HELLO READY" || reply == "ACK HELLO STOPPED" {
            timeout?.invalidate(); timeout = nil
            ready = reply == "ACK HELLO READY"
            stopped = reply == "ACK HELLO STOPPED"
            lastPong = Date()
            message = stopped ? "Glove connected. Check the area, then reset the stop." : "Glove connected and ready. Controls are locked."
            heartbeat?.invalidate()
            heartbeat = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
                guard let self, self.peripheral?.state == .connected else { return }
                if Date().timeIntervalSince(self.lastPong) > 2 {
                    self.central?.cancelPeripheralConnection(peripheral)
                    self.clearConnection("Glove stopped responding. Movement is locked.")
                } else if self.pending == nil { self.write("PING") }
            }
        } else if reply == "PONG STOPPED" {
            lastPong = Date()
            stopped = true
            armed = false
            ready = false
            message = "Physical stop or safety watchdog is active. Check the glove before resetting."
        } else if reply == "PONG READY" {
            lastPong = Date()
        } else if reply.hasPrefix("ACK ") {
            let command = String(reply.dropFirst(4))
            guard command == pending else { return }
            timeout?.invalidate(); timeout = nil; pending = nil
            lastPong = Date()
            lastAcknowledgedAt = ISO8601DateFormatter().string(from: Date())
            switch command {
            case "ARM": armed = true; message = "Controls armed."
            case "DISARM": armed = false; message = "Controls locked."
            case "STOP": stopped = true; armed = false; ready = false; lastCommand = "STOPPED"; message = "Emergency stop acknowledged."
            case "RESET": stopped = false; armed = false; ready = true; lastCommand = "REST"; message = "Stop reset. Controls remain locked."
            case "OPEN", "CLOSE", "REST": lastCommand = command; message = "\(command.capitalized) command acknowledged."
            default: break
            }
        } else if reply.hasPrefix("ERR ") {
            if !ready && !stopped {
                clearConnection("Glove setup failed: \(reply.dropFirst(4)). Check firmware and the physical stop.")
                central?.cancelPeripheralConnection(peripheral)
                return
            }
            timeout?.invalidate(); timeout = nil; pending = nil
            armed = false
            message = "Glove rejected command: \(reply.dropFirst(4))"
        }
        publish()
    }

    func peripheral(_ peripheral: CBPeripheral, didWriteValueFor characteristic: CBCharacteristic, error: Error?) {
        guard let error else { return }
        clearConnection("Bluetooth write failed: \(error.localizedDescription)")
        central?.cancelPeripheralConnection(peripheral)
    }
}
