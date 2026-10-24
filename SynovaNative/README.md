# Synova for macOS

This package displays the complete Synova interface as a native macOS app. The
web interface is bundled inside the application, so it does not require a local
server or an internet connection.

## Open in Xcode

1. Install the full Xcode app from the Mac App Store.
2. Open `SynovaNative/Package.swift` in Xcode.
3. Choose the **Synova** scheme and **My Mac** destination.
4. Press the Run button.

After changing the React interface, run `npm run native:assets` once before
opening Xcode again. Use `npm run native:run` to build and launch the same app
from Terminal.

If full Xcode is not installed yet, `npm run native:build-local` creates a
standalone `Synova.app` with the installed macOS command-line tools. Launch that
preview with `npm run native:launch-local`.
