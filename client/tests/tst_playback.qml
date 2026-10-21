import QtQuick
import QtTest
import "../lib/playback.js" as PB

// applyEvent is the daemon-event -> state reducer. It is a pure function over a plain state object
// so this runs under qmltestrunner without Quickshell (Playback imports Daemon -> Quickshell). Each
// case checks a rule that is easy to get wrong: a track change resetting the transport, an in-place
// queue splice, and the seek-drag guard that keeps position echoes from fighting the held thumb.
TestCase {
    name: "Playback"

    function freshState() {
        return {
            now: null, queue: { items: [], currentIndex: 0 },
            position: 0, duration: 0, paused: false, volume: 100,
            stopAfterCurrent: false, rating: "indifferent",
            pendingVideoId: "pending", lastError: "old",
            seekDrag: NaN, volDrag: false,
            lyrics: { synced: false, lines: [] }, auth: { signedIn: false },
            settings: ({}), lt: { role: "none" }
        };
    }

    // A track change resets duration from the new row and snaps position to 0.
    function test_now_playing_resets_position_and_duration() {
        var s = freshState();
        s.position = 42; s.duration = 100;
        PB.applyEvent(s, "now-playing", { videoId: "abc", duration: "2:53", rating: "like" });
        compare(s.duration, 173);
        compare(s.position, 0);
        compare(s.now.videoId, "abc");
        compare(s.rating, "like");
        compare(s.pendingVideoId, null);
        compare(s.lastError, null);
    }

    // queue-index keeps the array already held and patches only the current row.
    function test_queue_index_splices_current_row() {
        var s = freshState();
        s.queue = { items: [{ video_id: "a" }, { video_id: "b" }, { video_id: "c" }], currentIndex: 0 };
        var items = s.queue.items;
        PB.applyEvent(s, "queue-index", {
            current: { video_id: "b2", title: "Patched" }, currentIndex: 1,
            playedFrom: 0, shuffle: false, repeat: "off", sourceName: "Liked Music"
        });
        compare(s.queue.items.length, 3);
        compare(s.queue.items[1].video_id, "b2");   // current row patched in
        compare(s.queue.items[0].video_id, "a");    // the others are untouched
        compare(s.queue.currentIndex, 1);
        compare(s.queue.sourceName, "Liked Music");
        verify(s.queue.items === items);            // same array kept, not rebuilt
    }

    // position is applied normally, but ignored while a seek drag pins the thumb, then resumes.
    function test_position_ignored_while_seek_dragging() {
        var s = freshState();
        s.duration = 200;
        PB.applyEvent(s, "position", { position: 12.5 });
        compare(s.position, 12.5);                  // applied when not dragging
        s.seekDrag = 80;
        PB.applyEvent(s, "position", { position: 30 });
        compare(s.position, 12.5);                  // echo suppressed under the thumb
        s.seekDrag = NaN;
        PB.applyEvent(s, "position", { position: 30 });
        compare(s.position, 30);                    // applied again on release
    }

    // volume is applied from the daemon, unless the slider is being dragged.
    function test_volume_ignored_while_volume_dragging() {
        var s = freshState();
        PB.applyEvent(s, "volume", 42);
        compare(s.volume, 42);
        s.volDrag = true;
        PB.applyEvent(s, "volume", 90);
        compare(s.volume, 42);                      // echo ignored mid-drag
    }

    // A late startup restore (the snapshot said signedIn:false) must clear the sign-in gate.
    function test_spotify_restore_announcement_signs_the_client_in() {
        var s = freshState();
        s.spotify = { signedIn: false, stored: true, name: null, premium: null };
        compare(PB.applyEvent(s, "spotify-auth", { state: "restored" }), null);
        compare(s.spotify.signedIn, true);
        compare(s.spotify.stored, true);
        compare(s.spotify.premium, true);
        // A dead cached session says why instead of silently demanding a sign-in.
        PB.applyEvent(s, "spotify-auth", { state: "restore_failed", message: "bad credentials" });
        compare(s.spotify.signedIn, false);
        compare(s.spotify.stored, true);
        compare(s.spotify.error, "bad credentials");
    }

    // The SoundCloud browser flow drives its own mirror: waiting, sign-in, expiry, sign-out.
    // The TIDAL device flow carries a code the user types elsewhere, so "waiting" has to keep it
    // where the settings page can show it; every other state clears it again.
    function test_tidal_device_flow_carries_its_code() {
        var s = { tidal: { signedIn: false, hasCredentials: true } };
        var waiting = PB.applyEvent(s, "tidal-auth",
            { state: "waiting", code: "ABCD", url: "https://link.tidal.com/ABCD" });
        compare(s.tidal.code, "ABCD");
        compare(s.tidal.url, "https://link.tidal.com/ABCD");
        verify(waiting && waiting.toast.indexOf("ABCD") >= 0);

        // The ceiling rides along on the sign-in, because nothing re-reads it afterwards: without
        // it the settings page says the best reachable quality is unknown for the whole session.
        var done = PB.applyEvent(s, "tidal-auth",
            { state: "signed_in", name: "vlad", quality: "LOSSLESS" });
        compare(s.tidal.signedIn, true);
        compare(s.tidal.name, "vlad");
        compare(s.tidal.quality, "LOSSLESS");
        compare(s.tidal.code, "");
        verify(done && done.kind === "success");

        PB.applyEvent(s, "tidal-auth", { state: "signed_out" });
        compare(s.tidal.signedIn, false);
        compare(s.tidal.hasCredentials, true, "signing out must not forget the client id");
    }

    // The expiry TIDAL declares itself has to read the same as the one the daemon times out on.
    function test_tidal_expiry_reads_the_same_whoever_declares_it() {
        var s = { tidal: { signedIn: false, hasCredentials: true } };
        PB.applyEvent(s, "tidal-auth", { state: "waiting", code: "ABCD", url: "u" });
        var gone = PB.applyEvent(s, "tidal-auth", { state: "expired" });
        compare(s.tidal.code, "", "an expired code must not stay on screen");
        compare(s.tidal.signedIn, false);
        verify(gone && gone.toast.indexOf("expired") >= 0);
    }

    function test_soundcloud_auth_events_mirror_the_browser_flow() {
        var s = freshState();
        s.soundcloud = { signedIn: false, name: null, error: "" };
        // Opening the browser is progress, not an error: an info toast plus a guidance line.
        var wait = PB.applyEvent(s, "soundcloud-auth", { state: "waiting" });
        compare(wait.kind, "info");
        compare(s.soundcloud.signedIn, false);
        verify(s.soundcloud.error.indexOf("browser") >= 0);
        // Importing the session from the browser completes the sign-in.
        var fx = PB.applyEvent(s, "soundcloud-auth", { state: "signed_in", name: "nero" });
        compare(s.soundcloud.signedIn, true);
        compare(s.soundcloud.name, "nero");
        compare(s.soundcloud.error, "");
        compare(fx.kind, "success");
        // Giving up clears the guidance line with a calm info toast, not an error.
        var expired = PB.applyEvent(s, "soundcloud-auth", { state: "expired" });
        compare(expired.kind, "info");
        compare(s.soundcloud.signedIn, false);
        compare(s.soundcloud.error, "");
        // An expired persisted token reports itself and keeps the reason for the settings row.
        PB.applyEvent(s, "soundcloud-auth", { state: "restore_failed", message: "expired" });
        compare(s.soundcloud.signedIn, false);
        compare(s.soundcloud.error, "expired");
        PB.applyEvent(s, "soundcloud-auth", { state: "signed_out" });
        compare(s.soundcloud.signedIn, false);
        compare(s.soundcloud.error, "");
    }

    function test_queue_index_with_null_source_and_full_error_payload() {
        var s = freshState();
        s.queue = { items: [{ video_id: "a" }], currentIndex: 0 };
        PB.applyEvent(s, "queue-index", {
            currentIndex: 0, playedFrom: 0, shuffle: false, repeat: "off",
            sourceName: null, current: { video_id: "a", duration: "3:11" }
        });
        compare(s.queue.sourceName, null);
        compare(s.queue.items[0].duration, "3:11");

        var fx = PB.applyEvent(s, "playback-error",
            { videoId: "abc", message: "Could not load this track" });
        compare(s.lastError, "Could not load this track");
        compare(s.pendingVideoId, null);
        compare(fx.kind, "error");
    }

    function test_queue_changed_replaces_the_rows_wholesale() {
        var s = freshState();
        s.queue = { items: [{ video_id: "old" }], currentIndex: 0 };
        PB.applyEvent(s, "queue-changed", {
            items: [{ video_id: "x" }, { video_id: "y" }], currentIndex: 1,
            playedFrom: 0, shuffle: true, repeat: "all", sourceName: "Album"
        });
        compare(s.queue.items.length, 2);
        compare(s.queue.currentIndex, 1);
        compare(s.queue.shuffle, true);
        compare(s.queue.repeat, "all");
        compare(s.queue.sourceName, "Album");
    }

    function test_now_playing_with_null_rating_falls_back_to_indifferent() {
        var s = freshState();
        PB.applyEvent(s, "now-playing", {
            videoId: "abc", title: "Song", artists: "Artist", artistId: "UC1",
            artistRuns: [{ text: "Artist", id: "UC1" }], thumbnail: "t.jpg",
            duration: "3:00", streamClient: "android", rating: null
        });
        compare(s.rating, "indifferent");
        compare(s.duration, 180);
        compare(s.now.streamClient, "android");
        compare(s.now.artistRuns.length, 1);
    }

    function test_bare_transport_scalars_and_stop_after_current() {
        var s = freshState();
        PB.applyEvent(s, "duration", { duration: 210 });
        compare(s.duration, 210);
        PB.applyEvent(s, "stop-after-current", true);
        compare(s.stopAfterCurrent, true);
        PB.applyEvent(s, "stop-after-current", false);
        compare(s.stopAfterCurrent, false);
        PB.applyEvent(s, "playback-state", "playing");
        compare(s.paused, false);
        PB.applyEvent(s, "playback-state", "paused");
        compare(s.paused, true);
    }

    function test_auth_changed_accepts_the_signed_out_minimal_shape() {
        var s = freshState();
        s.auth = { signedIn: true, name: "ada" };
        PB.applyEvent(s, "auth-changed", { signedIn: false });
        compare(s.auth.signedIn, false);
        compare(s.auth.name, undefined);
    }

    function test_provider_changed_sets_the_active_provider() {
        var s = freshState();
        PB.applyEvent(s, "provider-changed", { provider: "spotify" });
        compare(s.provider, "spotify");
    }

    function test_lt_state_and_notice_shapes() {
        var s = freshState();
        var snap = {
            status: "disconnected", role: "none", requesting: false, roomCode: null,
            myId: null, serverUrl: "wss://example.invalid", users: [], currentTrack: null,
            queue: [], pendingJoins: [], suggestions: []
        };
        compare(PB.applyEvent(s, "lt-state", snap), null);
        compare(s.lt.role, "none");
        compare(s.lt.serverUrl, "wss://example.invalid");
        var notice = PB.applyEvent(s, "lt-notice", "ada joined");
        compare(notice.toast, "ada joined");
        compare(notice.kind, "info");
    }
}
