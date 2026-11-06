pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven { url = uri("https://jitpack.io") }
    }
}

rootProject.name = "AndroidResourceLab"
include(":app", ":mamu", ":lumen")
project(":lumen").projectDir = file("lumen-android")
project(":mamu").projectDir = file("vendor/Mamu/app")
