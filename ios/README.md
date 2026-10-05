# Bfxr for iOS

A native iPhone/iPad app that runs the same Bfxr web app bundled inside it, so
every synth tab works offline and stays in step with the website.

## Building

1. Open `ios/Bfxr.xcodeproj` in Xcode 15 or later.
2. Select the **Bfxr** target → *Signing & Capabilities*, pick your team, and
   change the bundle identifier (`net.bfxr.app`) if you need to.
3. Run on a simulator or device. iOS 15 or later is required.

There is no copy step: the project references `index.html`, `js/`, `css/`,
`img/` and `favicon.png` from the repository root, so every build picks up the
current web app.

CI (`.github/workflows/ios.yml`) builds the app for the simulator and for
devices, then launches it with `-BfxrSmokeTest`. In that mode it checks that the
tabs load, a sound renders, `localStorage` works and the bridge is installed,
then exits.

## How it works

| Piece | What it does |
| --- | --- |
| `BundleSchemeHandler.swift` | Serves the bundled files at `bfxr://app/…`. A stable origin keeps your saved sounds (`localStorage`) between launches. |
| `NativeBridge.js` | Injected before the page's scripts. It sends downloads (`<a download>`) to the share sheet, sends file inputs to the document picker, bridges `navigator.clipboard` to the system pasteboard, and resumes audio after interruptions. |
| `WebViewController.swift` | Hosts the `WKWebView` and answers the bridge. It also shows `alert`/`confirm`/`prompt`, opens outside links in Safari and reloads if WebKit's content process stops. |
| `SceneDelegate.swift` | Opens `.bfxr` and `.bcol` files sent to the app from Files, AirDrop, Mail and other apps. |
| `AppDelegate.swift` | Uses the `.playback` audio session, so sounds play with the silent switch on. |

The app differs from the website in a few ways:

- **Export WAV**, **Export All**, **Save .bfxr** and **Save .bcol** open the
  share sheet (Save to Files, AirDrop, …).
- **Open Data** opens the document picker. The app registers the `.bfxr` and
  `.bcol` file types, so you can also tap these files in Files.
- **Copy Link** produces a `https://www.bfxr.net/?sfx=…` link.
- The footer drops the sponsor/PayPal links, because App Store rules don't
  allow outside payment links.

On screens narrower than 640px (phones, and the website on phones), the panels
stack vertically and the tab strip scrolls sideways (`css/index.css`).
