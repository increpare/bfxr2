import UIKit

final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    private let webViewController = WebViewController()

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: windowScene)
        window.rootViewController = webViewController
        window.makeKeyAndVisible()
        self.window = window

        // Launched by opening a .bfxr/.bcol file from Files, AirDrop, Mail, ...
        open(connectionOptions.urlContexts)
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        open(URLContexts)
    }

    func sceneDidBecomeActive(_ scene: UIScene) {
        webViewController.resumeAudio()
    }

    private func open(_ contexts: Set<UIOpenURLContext>) {
        for context in contexts where context.url.isFileURL {
            webViewController.openDocument(at: context.url)
        }
    }
}
