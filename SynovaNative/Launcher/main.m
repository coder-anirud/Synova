#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

@interface SynovaAppDelegate : NSObject <NSApplicationDelegate>
@property(nonatomic, strong) NSWindow *window;
@property(nonatomic, strong) WKWebView *webView;
@end

@implementation SynovaAppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    NSRect frame = NSMakeRect(0, 0, 1440, 900);
    NSWindowStyleMask style = NSWindowStyleMaskTitled |
                              NSWindowStyleMaskClosable |
                              NSWindowStyleMaskMiniaturizable |
                              NSWindowStyleMaskResizable |
                              NSWindowStyleMaskFullSizeContentView;

    self.window = [[NSWindow alloc] initWithContentRect:frame
                                              styleMask:style
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    self.window.title = @"Synova";
    self.window.titleVisibility = NSWindowTitleHidden;
    self.window.titlebarAppearsTransparent = YES;
    self.window.movableByWindowBackground = YES;
    self.window.minSize = NSMakeSize(980, 680);

    WKWebViewConfiguration *configuration = [[WKWebViewConfiguration alloc] init];
    configuration.websiteDataStore = WKWebsiteDataStore.defaultDataStore;
    self.webView = [[WKWebView alloc] initWithFrame:self.window.contentView.bounds
                                      configuration:configuration];
    self.webView.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    self.webView.allowsMagnification = YES;
    [self.window.contentView addSubview:self.webView];

    NSString *indexPath = [NSBundle.mainBundle pathForResource:@"index"
                                                        ofType:@"html"
                                                   inDirectory:@"Web"];
    if (indexPath != nil) {
        NSURL *indexURL = [NSURL fileURLWithPath:indexPath];
        [self.webView loadFileURL:indexURL
           allowingReadAccessToURL:indexURL.URLByDeletingLastPathComponent];
    } else {
        [self.webView loadHTMLString:@"<main style='font:17px -apple-system;padding:40px'><h1>Synova could not open.</h1><p>The bundled interface is missing.</p></main>"
                               baseURL:nil];
    }

    [self.window center];
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    return YES;
}

- (void)reloadSynova:(id)sender {
    [self.webView reload];
}

@end

static void ConfigureMainMenu(void) {
    NSMenu *mainMenu = [[NSMenu alloc] initWithTitle:@""];
    NSMenuItem *appMenuItem = [[NSMenuItem alloc] initWithTitle:@"" action:nil keyEquivalent:@""];
    [mainMenu addItem:appMenuItem];

    NSMenu *appMenu = [[NSMenu alloc] initWithTitle:@"Synova"];
    [appMenu addItemWithTitle:@"About Synova"
                       action:@selector(orderFrontStandardAboutPanel:)
                keyEquivalent:@""];
    [appMenu addItem:[NSMenuItem separatorItem]];
    [appMenu addItemWithTitle:@"Reload Synova"
                       action:@selector(reloadSynova:)
                keyEquivalent:@"r"];
    [appMenu addItem:[NSMenuItem separatorItem]];
    [appMenu addItemWithTitle:@"Quit Synova"
                       action:@selector(terminate:)
                keyEquivalent:@"q"];
    appMenuItem.submenu = appMenu;
    NSApp.mainMenu = mainMenu;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSApplication *application = NSApplication.sharedApplication;
        application.activationPolicy = NSApplicationActivationPolicyRegular;
        ConfigureMainMenu();

        static SynovaAppDelegate *delegate;
        delegate = [[SynovaAppDelegate alloc] init];
        application.delegate = delegate;
        [application run];
    }
    return 0;
}
