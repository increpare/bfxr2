import UniformTypeIdentifiers
import WebKit

/// Serves the web app's files out of the app bundle under `bfxr://app/...`.
///
/// Using a custom scheme rather than `file://` URLs gives the page a stable
/// origin, so `localStorage` (where Bfxr keeps your sounds) persists between
/// launches, and `fetch` of `blob:`/`data:` URLs behaves as it does on the web.
final class BundleSchemeHandler: NSObject, WKURLSchemeHandler {
    static let scheme = "bfxr"
    static let host = "app"
    static let startURL = URL(string: "\(scheme)://\(host)/index.html")!

    /// Only these top-level paths are web content; everything else in the bundle stays private.
    private static let servedRoots: Set<String> = ["index.html", "favicon.png", "favicon.ico", "js", "css", "img"]

    private let root: URL

    init(root: URL = Bundle.main.resourceURL!) {
        self.root = root.standardizedFileURL
    }

    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        guard let url = urlSchemeTask.request.url else {
            urlSchemeTask.didFailWithError(URLError(.badURL))
            return
        }

        guard let fileURL = resolve(url), let data = try? Data(contentsOf: fileURL) else {
            let response = HTTPURLResponse(url: url, statusCode: 404, httpVersion: "HTTP/1.1", headerFields: nil)!
            urlSchemeTask.didReceive(response)
            urlSchemeTask.didReceive(Data())
            urlSchemeTask.didFinish()
            return
        }

        let headers = [
            "Content-Type": Self.mimeType(for: fileURL),
            "Content-Length": String(data.count),
            "Cache-Control": "no-cache",
        ]
        let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: headers)!
        urlSchemeTask.didReceive(response)
        urlSchemeTask.didReceive(data)
        urlSchemeTask.didFinish()
    }

    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) {
        // Responses are delivered synchronously, so there is nothing to cancel.
    }

    private func resolve(_ url: URL) -> URL? {
        guard url.host == Self.host else { return nil }
        var path = url.path
        if path.isEmpty || path == "/" { path = "/index.html" }
        let components = path.split(separator: "/").map(String.init)
        guard let first = components.first, Self.servedRoots.contains(first),
              !components.contains("..") else { return nil }

        let fileURL = root.appendingPathComponent(components.joined(separator: "/")).standardizedFileURL
        guard fileURL.path.hasPrefix(root.path + "/") else { return nil }
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: fileURL.path, isDirectory: &isDirectory),
              !isDirectory.boolValue else { return nil }
        return fileURL
    }

    private static func mimeType(for url: URL) -> String {
        switch url.pathExtension.lowercased() {
        case "html": return "text/html; charset=utf-8"
        case "js": return "text/javascript; charset=utf-8"
        case "css": return "text/css; charset=utf-8"
        case "json": return "application/json; charset=utf-8"
        default:
            return UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
        }
    }
}
