import AppKit
import SwiftUI
import WebKit

struct SynovaWebView: NSViewRepresentable {
    func makeNSView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.preferences.isElementFullscreenEnabled = true

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.allowsMagnification = true
        webView.setValue(false, forKey: "drawsBackground")

        loadApp(in: webView)
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) { }

    private func loadApp(in webView: WKWebView) {
        guard let indexURL = Bundle.module.url(
            forResource: "index",
            withExtension: "html",
            subdirectory: "Web"
        ) else {
            webView.loadHTMLString(
                "<main style='font: 17px -apple-system; padding: 40px'><h1>Synova could not open.</h1><p>The app files are missing. Rebuild the native assets and try again.</p></main>",
                baseURL: nil
            )
            return
        }

        webView.loadFileURL(
            indexURL,
            allowingReadAccessTo: indexURL.deletingLastPathComponent()
        )
    }
}
