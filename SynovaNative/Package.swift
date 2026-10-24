// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "Synova",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "Synova", targets: ["SynovaNative"])
    ],
    targets: [
        .executableTarget(
            name: "SynovaNative",
            resources: [
                .copy("Resources/Web")
            ]
        )
    ]
)
