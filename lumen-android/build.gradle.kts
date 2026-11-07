plugins {
    id("com.android.application") version "8.13.1"
    id("org.jetbrains.kotlin.android") version "2.2.21"
}

android {
    namespace = "com.lexo.lumen"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.lexo.lumen"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("dev.ffmpegkit-maintained:llama-android:0.1.1")
}
