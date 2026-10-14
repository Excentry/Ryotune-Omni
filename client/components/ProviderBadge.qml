import QtQuick
import "../"
import "../lib/ids.js" as Ids

// The source tag a card's artwork wears: the catalogue's glyph in its own colour on a dark chip,
// so YouTube Music, Spotify and SoundCloud items tell apart on any cover. Hidden for Ryotunes' own
// collections, which come from no catalogue.
Rectangle {
    id: root

    property string itemId: ""
    property int glyphSize: Style.sp(4)

    readonly property string glyph: Ids.sourceGlyph(root.itemId)

    visible: root.glyph !== ""
    width: root.glyphSize + Style.sp(2)
    height: width
    radius: width / 2
    // A fixed dark chip, not a skin token: it sits on arbitrary artwork and has to read on all of it.
    color: Qt.rgba(0, 0, 0, 0.6)
    border.width: 1
    border.color: Qt.rgba(1, 1, 1, 0.14)

    Icon {
        anchors.centerIn: parent
        name: root.glyph
        size: root.glyphSize
        color: Style.providerColors[Ids.providerOf(root.itemId)] || "white"
    }
}
