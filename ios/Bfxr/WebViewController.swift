import UIKit
import UniformTypeIdentifiers
import WebKit

/// Hosts the Bfxr web app and provides the native pieces a browser would:
/// saving files, opening files, the clipboard and JavaScript dialogs.
final class WebViewController: UIViewController {
    private static let pageColor = UIColor(red: 0xE7 / 255, green: 0xD1 / 255, blue: 0xA7 / 255, alpha: 1)
    private static let isSmokeTest = ProcessInfo.processInfo.arguments.contains("-BfxrSmokeTest")

    private var webView: WKWebView!
    private var hasLoaded = false
    private var pendingDocuments: [URL] = []
    private var pendingOpenReply: ((Any?, String?) -> Void)?

    override func loadView() {
        let configuration = WKWebViewConfiguration()
        configuration.setURLSchemeHandler(BundleSchemeHandler(), forURLScheme: BundleSchemeHandler.scheme)
        configuration.mediaTypesRequiringUserActionForPlayback = []
        configuration.allowsInlineMediaPlayback = true

        let controller = configuration.userContentController
        controller.addScriptMessageHandler(WeakMessageHandler(self), contentWorld: .page, name: "bfxr")
        if let url = Bundle.main.url(forResource: "NativeBridge", withExtension: "js"),
           let source = try? String(contentsOf: url, encoding: .utf8) {
            controller.addUserScript(WKUserScript(source: source, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        } else {
            assertionFailure("NativeBridge.js missing from the app bundle")
        }

        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsLinkPreview = false
        webView.isOpaque = false
        webView.backgroundColor = Self.pageColor
        webView.scrollView.backgroundColor = Self.pageColor
        #if DEBUG
        if #available(iOS 16.4, *) { webView.isInspectable = true }
        #endif
        view = webView
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        webView.load(URLRequest(url: BundleSchemeHandler.startURL))
    }

    // MARK: - Called by the scene

    func resumeAudio() {
        guard hasLoaded else { return }
        webView.evaluateJavaScript("window.__bfxrResumeAudio && window.__bfxrResumeAudio()")
    }

    /// Loads a .bfxr or .bcol file that another app handed to us.
    func openDocument(at url: URL) {
        guard hasLoaded else {
            pendingDocuments.append(url)
            return
        }
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        guard let data = try? Data(contentsOf: url) else {
            presentAlert(message: "Could not read \(url.lastPathComponent).")
            return
        }
        webView.callAsyncJavaScript(
            "window.__bfxrOpenDocument(name, base64)",
            arguments: ["name": url.lastPathComponent, "base64": data.base64EncodedString()],
            in: nil,
            in: .page
        )
    }

    // MARK: - Bridge actions

    fileprivate func handle(_ body: [String: Any], reply: @escaping (Any?, String?) -> Void) {
        switch body["action"] as? String {
        case "clipboardWrite":
            UIPasteboard.general.string = body["text"] as? String ?? ""
            reply(nil, nil)
        case "clipboardRead":
            reply(UIPasteboard.general.string ?? "", nil)
        case "saveFile":
            saveFile(body, reply: reply)
        case "openFile":
            openFile(accept: body["accept"] as? String ?? "", multiple: body["multiple"] as? Bool ?? false, reply: reply)
        case "log":
            NSLog("Bfxr [%@] %@", body["level"] as? String ?? "log", body["message"] as? String ?? "")
            reply(nil, nil)
        default:
            reply(nil, "Unknown action")
        }
    }

    private func saveFile(_ body: [String: Any], reply: @escaping (Any?, String?) -> Void) {
        guard let base64 = body["base64"] as? String,
              let data = Data(base64Encoded: base64) else {
            reply(nil, "Missing file data")
            return
        }
        let filename = Self.sanitizedFilename(body["filename"] as? String ?? "download")
        let folder = FileManager.default.temporaryDirectory
            .appendingPathComponent("Exports", isDirectory: true)
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let fileURL = folder.appendingPathComponent(filename)
        do {
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            try data.write(to: fileURL, options: .atomic)
        } catch {
            reply(nil, error.localizedDescription)
            return
        }

        let share = UIActivityViewController(activityItems: [fileURL], applicationActivities: nil)
        share.completionWithItemsHandler = { _, _, _, _ in
            try? FileManager.default.removeItem(at: folder)
        }
        anchorPopover(share.popoverPresentationController)
        topViewController.present(share, animated: true)
        reply(nil, nil)
    }

    private func openFile(accept: String, multiple: Bool, reply: @escaping (Any?, String?) -> Void) {
        pendingOpenReply?([], nil)
        pendingOpenReply = reply

        let types = Self.contentTypes(forAccept: accept)
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: types, asCopy: true)
        picker.allowsMultipleSelection = multiple
        picker.delegate = self
        topViewController.present(picker, animated: true)
    }

    // MARK: - Helpers

    static func contentTypes(forAccept accept: String) -> [UTType] {
        var types: [UTType] = []
        for token in accept.split(separator: ",") {
            let item = token.trimmingCharacters(in: .whitespaces)
            let type = item.hasPrefix(".")
                ? UTType(filenameExtension: String(item.dropFirst()))
                : UTType(mimeType: item)
            if let type, !types.contains(type) { types.append(type) }
        }
        // Bfxr's own files are JSON underneath; accept loosely typed copies too.
        if types.contains(where: { $0.conforms(to: .json) }) {
            types.append(contentsOf: [.json, .plainText])
        }
        return types.isEmpty ? [.item] : types
    }

    static func sanitizedFilename(_ name: String) -> String {
        let forbidden = CharacterSet(charactersIn: "/\\:\0").union(.newlines).union(.controlCharacters)
        let cleaned = name.components(separatedBy: forbidden).joined(separator: "_")
            .trimmingCharacters(in: .whitespaces)
        let safe = cleaned.isEmpty || cleaned.hasPrefix(".") ? "sound" + cleaned : cleaned
        return String(safe.prefix(200))
    }

    private var topViewController: UIViewController {
        var top: UIViewController = self
        while let presented = top.presentedViewController { top = presented }
        return top
    }

    private func anchorPopover(_ popover: UIPopoverPresentationController?) {
        guard let popover else { return }
        popover.sourceView = view
        popover.sourceRect = CGRect(x: view.bounds.midX, y: view.bounds.midY, width: 1, height: 1)
        popover.permittedArrowDirections = []
    }

    private func presentAlert(message: String) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        topViewController.present(alert, animated: true)
    }

    private func runSmokeTest() {
        // Used by CI: checks the bundled app boots and can synthesize a sound, then exits.
        let script = """
            await new Promise(resolve => setTimeout(resolve, 1500));
            localStorage.setItem('bfxr-smoke', 'ok');
            const result = {
                tabs: typeof tabs === 'undefined' ? -1 : tabs.length,
                wavBytes: typeof tabs === 'undefined' ? 0 : tabs[0].synth.generate_sound_uri().length,
                storage: localStorage.getItem('bfxr-smoke'),
                clipboard: typeof navigator.clipboard.readText,
                errors: window.__bfxrErrors || []
            };
            localStorage.removeItem('bfxr-smoke');
            return JSON.stringify(result);
            """
        webView.callAsyncJavaScript(script, arguments: [:], in: nil, in: .page) { result in
            var passed = false
            switch result {
            case .success(let value):
                let json = value as? String ?? "null"
                print("BFXR_SMOKE_RESULT \(json)")
                if let data = json.data(using: .utf8),
                   let info = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    passed = (info["tabs"] as? Int ?? 0) > 0
                        && (info["wavBytes"] as? Int ?? 0) > 1000
                        && info["storage"] as? String == "ok"
                        && info["clipboard"] as? String == "function"
                        && (info["errors"] as? [Any])?.isEmpty == true
                }
            case .failure(let error):
                print("BFXR_SMOKE_RESULT error: \(error)")
            }
            print(passed ? "BFXR_SMOKE_OK" : "BFXR_SMOKE_FAILED")
            fflush(stdout)
            exit(passed ? 0 : 1)
        }
    }
}

// MARK: - WKNavigationDelegate

extension WebViewController: WKNavigationDelegate {
    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
    ) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.cancel)
            return
        }
        switch url.scheme?.lowercased() ?? "" {
        case BundleSchemeHandler.scheme, "about", "blob", "data":
            decisionHandler(.allow)
        case "http", "https", "mailto":
            // Footer and About links open in Safari rather than replacing the app.
            UIApplication.shared.open(url)
            decisionHandler(.cancel)
        default:
            decisionHandler(.cancel)
        }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        hasLoaded = true
        let documents = pendingDocuments
        pendingDocuments.removeAll()
        documents.forEach(openDocument(at:))
        if Self.isSmokeTest { runSmokeTest() }
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        // Sounds are saved to localStorage as you work, so a reload loses nothing.
        hasLoaded = false
        webView.reload()
    }
}

// MARK: - WKUIDelegate

extension WebViewController: WKUIDelegate {
    func webView(
        _ webView: WKWebView,
        createWebViewWith configuration: WKWebViewConfiguration,
        for navigationAction: WKNavigationAction,
        windowFeatures: WKWindowFeatures
    ) -> WKWebView? {
        if let url = navigationAction.request.url,
           ["http", "https", "mailto"].contains(url.scheme?.lowercased() ?? "") {
            UIApplication.shared.open(url)
        }
        return nil
    }

    func webView(
        _ webView: WKWebView,
        runJavaScriptAlertPanelWithMessage message: String,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping () -> Void
    ) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler() })
        presentDialog(alert) { completionHandler() }
    }

    func webView(
        _ webView: WKWebView,
        runJavaScriptConfirmPanelWithMessage message: String,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping (Bool) -> Void
    ) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel) { _ in completionHandler(false) })
        alert.addAction(UIAlertAction(title: "OK", style: .destructive) { _ in completionHandler(true) })
        presentDialog(alert) { completionHandler(false) }
    }

    func webView(
        _ webView: WKWebView,
        runJavaScriptTextInputPanelWithPrompt prompt: String,
        defaultText: String?,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping (String?) -> Void
    ) {
        let alert = UIAlertController(title: nil, message: prompt, preferredStyle: .alert)
        alert.addTextField { $0.text = defaultText }
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel) { _ in completionHandler(nil) })
        alert.addAction(UIAlertAction(title: "OK", style: .default) { [weak alert] _ in
            completionHandler(alert?.textFields?.first?.text ?? "")
        })
        presentDialog(alert) { completionHandler(nil) }
    }

    /// WebKit requires every dialog's completion handler to be called, even if we can't show it.
    private func presentDialog(_ alert: UIAlertController, otherwise fallback: () -> Void) {
        guard view.window != nil, topViewController.isBeingDismissed == false else {
            fallback()
            return
        }
        topViewController.present(alert, animated: true)
    }
}

// MARK: - UIDocumentPickerDelegate

extension WebViewController: UIDocumentPickerDelegate {
    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
        let files: [[String: Any]] = urls.compactMap { url in
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            guard let data = try? Data(contentsOf: url) else { return nil }
            return [
                "name": url.lastPathComponent,
                "mimeType": UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "",
                "base64": data.base64EncodedString(),
            ]
        }
        pendingOpenReply?(files, nil)
        pendingOpenReply = nil
    }

    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
        pendingOpenReply?([], nil)
        pendingOpenReply = nil
    }
}

// MARK: - Script messages

/// WKUserContentController retains its handlers; this keeps it from retaining the controller.
private final class WeakMessageHandler: NSObject, WKScriptMessageHandlerWithReply {
    private weak var target: WebViewController?

    init(_ target: WebViewController) {
        self.target = target
    }

    func userContentController(
        _ userContentController: WKUserContentController,
        didReceive message: WKScriptMessage,
        replyHandler: @escaping (Any?, String?) -> Void
    ) {
        guard let target, let body = message.body as? [String: Any] else {
            replyHandler(nil, "Bad message")
            return
        }
        target.handle(body, reply: replyHandler)
    }
}
