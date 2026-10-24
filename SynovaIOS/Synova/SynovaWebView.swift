import SwiftUI
import UIKit
import WebKit

struct SynovaWebView: UIViewRepresentable {
    func makeCoordinator() -> Coordinator {
        Coordinator(runSmokeTest: ProcessInfo.processInfo.arguments.contains("--synova-smoke-test"), runMuseBridgeTest: ProcessInfo.processInfo.arguments.contains("--synova-muse-bridge-test"))
    }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        configuration.userContentController.add(context.coordinator, name: "synovaGlove")
        configuration.userContentController.add(context.coordinator, name: "synovaMuse")

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        context.coordinator.webView = webView
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.backgroundColor = UIColor(red: 0.96, green: 0.96, blue: 0.97, alpha: 1)
        webView.scrollView.contentInsetAdjustmentBehavior = .automatic
        webView.allowsBackForwardNavigationGestures = false

        guard let indexURL = Bundle.main.url(forResource: "index", withExtension: "html"),
              let resourceURL = Bundle.main.resourceURL else {
            webView.loadHTMLString(
                "<main style='font:17px -apple-system;padding:32px'><h1>Synova could not open.</h1><p>The bundled interface is missing.</p></main>",
                baseURL: nil
            )
            return webView
        }

        webView.loadFileURL(indexURL, allowingReadAccessTo: resourceURL)
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) { }

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
        weak var webView: WKWebView?
        private let runSmokeTest: Bool
        private let runMuseBridgeTest: Bool
        private var hasRunSmokeTest = false

        init(runSmokeTest: Bool, runMuseBridgeTest: Bool) {
            self.runSmokeTest = runSmokeTest
            self.runMuseBridgeTest = runMuseBridgeTest
            super.init()
            GloveBLEManager.shared.onUpdate = { [weak self] status in
                guard let self, let webView = self.webView,
                      let data = try? JSONSerialization.data(withJSONObject: status),
                      let json = String(data: data, encoding: .utf8) else { return }
                webView.evaluateJavaScript("window.dispatchEvent(new CustomEvent('synova-glove', { detail: \(json) }));")
            }
        }

        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard message.frameInfo.isMainFrame,
                  let request = message.body as? [String: Any] else { return }
            if message.name == "synovaGlove" { GloveBLEManager.shared.handle(request) }
            if message.name == "synovaMuse" { requestMuse(request) }
        }

        private func requestMuse(_ request: [String: Any]) {
            guard let host = request["host"] as? String,
                  let token = request["token"] as? String,
                  let id = request["id"] as? String,
                  let action = request["action"] as? String,
                  ["status", "startRecording", "stopRecording"].contains(action),
                  token.count >= 16, token.count <= 128,
                  host.count <= 80, !host.contains("/"), !host.contains("@"),
                  !host.contains(" ") else {
                emitMuse(["id": request["id"] as? String ?? "", "error": "Enter the Mac address and access key shown by the bridge."])
                return
            }
            let parts = host.split(separator: ":", omittingEmptySubsequences: false)
            guard parts.count <= 2,
                  let port = parts.count == 2 ? Int(parts[1]) : 8765,
                  (1...65535).contains(port) else {
                emitMuse(["id": id, "error": "Use a valid Mac address and port."])
                return
            }
            let hostname = String(parts[0]).lowercased()
            let octets = hostname.split(separator: ".").compactMap { UInt8($0) }
            let isPrivateIPv4 = octets.count == 4 &&
                (octets[0] == 10 || octets[0] == 192 && octets[1] == 168 ||
                 octets[0] == 172 && (16...31).contains(octets[1]) ||
                 octets[0] == 127)
            let route = action == "startRecording" ? "/api/recording/start" : action == "stopRecording" ? "/api/recording/stop" : "/api/status"
            guard hostname == "localhost" || hostname.hasSuffix(".local") || isPrivateIPv4,
                  let url = URL(string: "http://\(hostname):\(port)\(route)") else {
                emitMuse(["id": id, "error": "Use a local Mac address, such as 192.168.1.5:8765."])
                return
            }
            var urlRequest = URLRequest(url: url)
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            urlRequest.timeoutInterval = 3
            if action != "status" {
                urlRequest.httpMethod = "POST"
                urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
                let label = action == "startRecording" ? (request["label"] as? String ?? "") : ""
                urlRequest.httpBody = try? JSONSerialization.data(withJSONObject: ["label": label])
            }
            URLSession.shared.dataTask(with: urlRequest) { [weak self] data, response, error in
                var result: [String: Any] = ["id": id]
                if let error { result["error"] = error.localizedDescription }
                else if (response as? HTTPURLResponse)?.statusCode == 401 { result["error"] = "The access key does not match the Mac bridge." }
                else if let data, let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    if let serverError = value["error"] as? String { result["error"] = serverError }
                    else { result["status"] = value }
                }
                else { result["error"] = "The Mac bridge returned an invalid response." }
                DispatchQueue.main.async { self?.emitMuse(result) }
            }.resume()
        }

        private func emitMuse(_ result: [String: Any]) {
            guard let webView,
                  let data = try? JSONSerialization.data(withJSONObject: result),
                  let json = String(data: data, encoding: .utf8) else { return }
            webView.evaluateJavaScript("window.dispatchEvent(new CustomEvent('synova-muse', { detail: \(json) }));")
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            guard let url = navigationAction.request.url else {
                decisionHandler(.cancel)
                return
            }

            if url.isFileURL || url.scheme == "about" {
                decisionHandler(.allow)
            } else {
                UIApplication.shared.open(url)
                decisionHandler(.cancel)
            }
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            GloveBLEManager.shared.publishCurrent()
#if DEBUG
            guard (runSmokeTest || runMuseBridgeTest), !hasRunSmokeTest else { return }
            hasRunSmokeTest = true

            if runMuseBridgeTest {
                let museTest = #"""
                return await new Promise((resolve) => {
                  const timeout = setTimeout(() => resolve('timeout'), 5000);
                  const handler = (event) => {
                    if (event.detail.id !== 'smoke-muse') return;
                    clearTimeout(timeout);
                    window.removeEventListener('synova-muse', handler);
                    resolve(event.detail.status?.connected === false && Array.isArray(event.detail.status?.samples) ? 'passed' : JSON.stringify(event.detail));
                  };
                  window.addEventListener('synova-muse', handler);
                  window.webkit.messageHandlers.synovaMuse.postMessage({ action: 'status', host: '127.0.0.1:8765', token: 'synova-smoke-key-123456', id: 'smoke-muse' });
                });
                """#
                Task { @MainActor in
                    let result: String
                    do {
                        result = (try await webView.callAsyncJavaScript(museTest, arguments: [:], in: nil, contentWorld: .page)) as? String ?? "invalid result"
                    } catch { result = error.localizedDescription }
                    UserDefaults.standard.set(result, forKey: "SynovaMuseBridgeResult")
                    print("SYNOVA_MUSE_BRIDGE_RESULT \(result)")
                }
                if !runSmokeTest { return }
            }

            let smokeTest = #"""
            const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
            const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
            const buttons = () => Array.from(document.querySelectorAll('button'));
            const buttonNamed = (name, root = document) => Array.from(root.querySelectorAll('button')).find((button) => normalize(button.textContent) === name);
            const results = { passed: [], failed: [] };
            const check = (condition, name) => (condition ? results.passed : results.failed).push(name);

            await wait(500);
            check(document.title.includes('Dashboard'), 'Dashboard loaded');
            check(normalize(document.querySelector('h1')?.textContent) === 'Welcome to Synova', 'Synova welcome visible');

            document.querySelector('button[aria-label="Open navigation"]')?.click();
            await wait(150);
            check(document.querySelector('.sidebar')?.classList.contains('is-open'), 'Navigation drawer opens');
            document.querySelector('button[aria-label="Close navigation"]')?.click();
            await wait(100);
            check(document.querySelectorAll('.mobile-tab-bar button').length === 5, 'Five quick-navigation tabs available');

            buttonNamed('Sessions', document.querySelector('.mobile-tab-bar'))?.click();
            await wait(500);
            check(document.title.includes('Training Sessions'), 'Sessions tab navigation');

            document.querySelector('.session-actions button')?.click();
            await wait(150);
            check(normalize(document.querySelector('.session-timer span')?.textContent) === 'Session in progress', 'Session starts');
            buttonNamed('Add demo event')?.click();
            await wait(150);
            check(document.body.textContent.includes('Open intention detected'), 'Session event is recorded');

            buttonNamed('Glove', document.querySelector('.mobile-tab-bar'))?.click();
            await wait(500);
            check(document.title.includes('Glove Control'), 'Glove tab navigation');

            document.querySelector('.arm-control')?.click();
            await wait(100);
            check(document.querySelector('.arm-control')?.textContent.includes('Disarm controls'), 'Glove controls arm');
            buttonNamed('Close hand')?.click();
            await wait(100);
            check(normalize(document.querySelector('.current-command strong')?.textContent) === 'CLOSE', 'Close-hand command updates');
            document.querySelector('.emergency-button')?.click();
            await wait(100);
            check(document.body.textContent.includes('Emergency stop is active'), 'Emergency stop engages');

            buttonNamed('Settings', document.querySelector('.mobile-tab-bar'))?.click();
            await wait(500);
            check(document.title.includes('Settings'), 'Settings tab navigation');

            return JSON.stringify(results);
            """#

            Task { @MainActor in
                let value: String
                do {
                    let output = try await webView.callAsyncJavaScript(
                        smokeTest,
                        arguments: [:],
                        in: nil,
                        contentWorld: .page
                    )
                    value = output as? String ?? String(describing: output)
                } catch {
                    value = "{\"passed\":[],\"failed\":[\"JavaScript error: \(error.localizedDescription)\"]}"
                }
                UserDefaults.standard.set(value, forKey: "SynovaSmokeResult")
                print("SYNOVA_SMOKE_RESULT \(value)")
            }
#endif
        }
    }
}
