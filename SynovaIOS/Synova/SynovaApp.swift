import SwiftUI

@main
struct SynovaApp: App {
    var body: some Scene {
        WindowGroup {
            SynovaWebView()
                .background(Color(red: 0.96, green: 0.96, blue: 0.97))
                .preferredColorScheme(.light)
        }
    }
}
