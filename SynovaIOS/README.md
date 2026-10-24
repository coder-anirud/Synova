# Synova for iOS

Synova is packaged as a universal iOS app for iPhone and iPad. Its interface is
bundled into the application and does not require a development server or an
internet connection.

## Run in Xcode

1. Install the full Xcode app from the Mac App Store.
2. Open `Synova.xcodeproj`.
3. Select the **Synova** scheme.
4. Choose an iPhone or iPad Simulator.
5. Press **Run**.

For a physical iPhone, select your development team under **Signing &
Capabilities**, connect the phone, and choose it as the run destination.

After changing the React interface, run `npm run ios:prepare` to refresh the
offline interface bundle and app icon before building in Xcode.
