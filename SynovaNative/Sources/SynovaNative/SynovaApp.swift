import SwiftUI

@main
struct SynovaApp: App {
    var body: some Scene {
        WindowGroup("Synova") {
            SynovaWebView()
                .frame(minWidth: 980, minHeight: 680)
                .ignoresSafeArea()
        }
        .defaultSize(width: 1440, height: 900)
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(replacing: .newItem) { }
        }
    }
}
