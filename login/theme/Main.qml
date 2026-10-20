import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    width: 1280; height: 720
    color: "#f2f0e9"
    property bool busy: false
    function submit() {
        if (!busy && username.text.length && session.currentIndex >= 0) {
            busy = true; message.text = "Signing in…"
            sddm.login(username.text, password.text, session.currentIndex)
        }
    }
    Connections {
        target: sddm
        function onLoginFailed() {
            root.busy = false; password.clear()
            message.text = "Login failed. Check your username and password."
            password.forceActiveFocus()
        }
    }
    Rectangle {
        id: artwork
        anchors { top: parent.top; bottom: parent.bottom; right: parent.right; margins: 24 }
        width: parent.width * 0.53
        color: "#080a0c"; border.color: "#151515"; border.width: 4
        Image {
            id: portrait
            anchors.fill: parent; anchors.margins: 4
            source: "assets/ichigo.png"; fillMode: Image.PreserveAspectCrop
        }
        Rectangle {
            x: 20; y: 20; width: 170; height: 45; color: "#f2f0e9"; border.width: 3
            Text { anchors.centerIn: parent; text: "黒崎 一護"; font.pixelSize: 25; font.bold: true }
        }
        Rectangle {
            anchors { bottom: parent.bottom; right: parent.right; margins: 20 }
            width: 210; height: 62; color: "#f2f0e9"; border.width: 3; rotation: -4
            Text { anchors.centerIn: parent; text: "BANKAI."; font { pixelSize: 34; bold: true; italic: true } }
        }
    }
    Column {
        id: panel
        width: Math.min(360, parent.width * 0.35)
        anchors { verticalCenter: parent.verticalCenter; left: parent.left; leftMargin: parent.width * 0.065 }
        spacing: 13
        Text { text: "BLEACH / SOUL SOCIETY"; font { pixelSize: 12; bold: true; letterSpacing: 3 } }
        Text { text: "WELCOME\nBACK."; lineHeight: 0.85; font { pixelSize: 64; bold: true; italic: true } color: "#111111" }
        Rectangle { width: parent.width; height: 5; color: "#111111" }
        Text { text: "Sign in to your world."; font.pixelSize: 16; color: "#444444" }
        TextField {
            id: username; width: parent.width; height: 48
            text: userModel.lastUser; placeholderText: "Username"; enabled: !root.busy
            font.pixelSize: 17; color: "#111111"; leftPadding: 14
            background: Rectangle { color: "#faf9f5"; border.width: username.activeFocus ? 3 : 1; border.color: "#111111" }
            onAccepted: password.forceActiveFocus()
        }
        TextField {
            id: password; width: parent.width; height: 48
            placeholderText: "Password"; echoMode: TextInput.Password; enabled: !root.busy
            font.pixelSize: 17; color: "#111111"; leftPadding: 14
            background: Rectangle { color: "#faf9f5"; border.width: password.activeFocus ? 3 : 1; border.color: "#111111" }
            onAccepted: root.submit()
        }
        Text { text: keyboard.capsLock ? "Caps Lock is on" : ""; height: 16; font.pixelSize: 12 }
        ComboBox {
            id: session; width: parent.width; height: 40
            model: sessionModel; textRole: "name"; currentIndex: sessionModel.lastIndex
            enabled: !root.busy
            palette { button: "#faf9f5"; buttonText: "#111111"; text: "#111111"; base: "#faf9f5"; highlight: "#555555"; highlightedText: "white" }
        }
        Button {
            width: parent.width; height: 50; enabled: !root.busy
            contentItem: Text { text: root.busy ? "SIGNING IN…" : "ENTER  →"; color: "#faf9f5"; font { pixelSize: 17; bold: true; letterSpacing: 3 } horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { color: parent.down ? "#444444" : "#111111"; border.width: parent.activeFocus ? 3 : 0; border.color: "#888888" }
            onClicked: root.submit()
        }
        Text { id: message; width: parent.width; height: 34; wrapMode: Text.Wrap; font.pixelSize: 12; color: "#111111"; Accessible.role: Accessible.AlertMessage }
        Row {
            spacing: 10
            Button { text: "Restart"; visible: sddm.canReboot; onClicked: restartDialog.open() }
            Button { text: "Shut down"; visible: sddm.canPowerOff; onClicked: shutdownDialog.open() }
        }
    }
    Dialog {
        id: restartDialog; anchors.centerIn: parent; title: "Restart computer?"; modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel; onAccepted: sddm.reboot()
    }
    Dialog {
        id: shutdownDialog; anchors.centerIn: parent; title: "Shut down computer?"; modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel; onAccepted: sddm.powerOff()
    }
    Component.onCompleted: { if (username.text.length) password.forceActiveFocus(); else username.forceActiveFocus() }
}
