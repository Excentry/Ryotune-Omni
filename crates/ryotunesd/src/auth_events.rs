use serde_json::{json, Value};

pub fn spotify_restored() -> Value {
    json!({ "state": "restored" })
}

pub fn spotify_restore_failed(message: &str) -> Value {
    json!({ "state": "restore_failed", "message": message })
}

pub fn spotify_url(url: &str) -> Value {
    json!({ "state": "url", "url": url })
}

pub fn spotify_signed_in(name: Option<&str>) -> Value {
    json!({ "state": "signed_in", "name": name })
}

pub fn spotify_signed_out() -> Value {
    json!({ "state": "signed_out" })
}

pub fn spotify_error(message: &str) -> Value {
    json!({ "state": "error", "message": message })
}

pub fn soundcloud_signed_in(name: &str) -> Value {
    json!({ "state": "signed_in", "name": name })
}

pub fn soundcloud_waiting() -> Value {
    json!({ "state": "waiting" })
}

pub fn soundcloud_expired(message: &str) -> Value {
    json!({ "state": "expired", "message": message })
}

pub fn soundcloud_restore_failed(message: &str) -> Value {
    json!({ "state": "restore_failed", "message": message })
}

pub fn soundcloud_signed_out() -> Value {
    json!({ "state": "signed_out" })
}

pub fn soundcloud_error(message: &str) -> Value {
    json!({ "state": "error", "message": message })
}

pub fn tidal_signed_out() -> Value {
    json!({ "state": "signed_out" })
}

pub fn tidal_waiting(url: &str, code: &str) -> Value {
    json!({ "state": "waiting", "url": url, "code": code })
}

pub fn tidal_signed_in(name: Option<&str>, quality: &str) -> Value {
    json!({ "state": "signed_in", "name": name, "quality": quality })
}

pub fn tidal_expired(message: &str) -> Value {
    json!({ "state": "expired", "message": message })
}

pub fn tidal_error(message: &str) -> Value {
    json!({ "state": "error", "message": message })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    fn state_of(v: &Value) -> &str {
        v["state"].as_str().expect("state tag is a string")
    }

    #[test]
    fn spotify_auth_states_carry_their_companion_fields() {
        assert_eq!(spotify_restored(), json!({ "state": "restored" }));
        assert_eq!(spotify_signed_out(), json!({ "state": "signed_out" }));
        let failed = spotify_restore_failed("dead");
        assert_eq!(state_of(&failed), "restore_failed");
        assert_eq!(failed["message"], "dead");
        let url = spotify_url("https://accounts.spotify.com/oauthorize");
        assert_eq!(state_of(&url), "url");
        assert_eq!(url["url"], "https://accounts.spotify.com/oauthorize");
        let signed_in = spotify_signed_in(Some("Ada"));
        assert_eq!(state_of(&signed_in), "signed_in");
        assert_eq!(signed_in["name"], "Ada");
        assert!(spotify_signed_in(None)["name"].is_null());
        let error = spotify_error("nope");
        assert_eq!(state_of(&error), "error");
        assert_eq!(error["message"], "nope");
    }

    #[test]
    fn soundcloud_auth_states_carry_their_companion_fields() {
        let signed_in = soundcloud_signed_in("ada");
        assert_eq!(state_of(&signed_in), "signed_in");
        assert_eq!(signed_in["name"], "ada");
        assert_eq!(soundcloud_waiting(), json!({ "state": "waiting" }));
        assert_eq!(soundcloud_signed_out(), json!({ "state": "signed_out" }));
        for (payload, tag) in [
            (soundcloud_expired("timeout"), "expired"),
            (soundcloud_restore_failed("session gone"), "restore_failed"),
            (soundcloud_error("browser"), "error"),
        ] {
            assert_eq!(state_of(&payload), tag);
            assert!(payload["message"].is_string());
        }
    }

    #[test]
    fn tidal_auth_states_carry_their_companion_fields() {
        assert_eq!(tidal_signed_out(), json!({ "state": "signed_out" }));
        let waiting = tidal_waiting("https://tidal.com/link", "ABCD-EFGH");
        assert_eq!(state_of(&waiting), "waiting");
        assert_eq!(waiting["url"], "https://tidal.com/link");
        assert_eq!(waiting["code"], "ABCD-EFGH");
        let signed_in = tidal_signed_in(Some("Ada"), "HI_RES");
        assert_eq!(state_of(&signed_in), "signed_in");
        assert_eq!(signed_in["name"], "Ada");
        assert_eq!(signed_in["quality"], "HI_RES");
        assert!(tidal_signed_in(None, "LOSSLESS")["name"].is_null());
        for payload in [tidal_expired("expired"), tidal_error("boom")] {
            assert!(payload["message"].is_string());
        }
    }

    #[test]
    fn auth_payloads_never_carry_companion_keys_on_bare_states() {
        for payload in [
            spotify_restored(),
            spotify_signed_out(),
            soundcloud_waiting(),
            soundcloud_signed_out(),
            tidal_signed_out(),
        ] {
            let obj = payload.as_object().expect("object payload");
            assert_eq!(obj.len(), 1, "bare state must carry only its tag: {payload}");
        }
    }

    #[test]
    fn every_auth_payload_is_a_flat_object_with_a_string_state() {
        let all = [
            spotify_restored(),
            spotify_restore_failed("m"),
            spotify_url("u"),
            spotify_signed_in(Some("n")),
            spotify_signed_out(),
            spotify_error("m"),
            soundcloud_signed_in("n"),
            soundcloud_waiting(),
            soundcloud_expired("m"),
            soundcloud_restore_failed("m"),
            soundcloud_signed_out(),
            soundcloud_error("m"),
            tidal_signed_out(),
            tidal_waiting("u", "c"),
            tidal_signed_in(Some("n"), "q"),
            tidal_expired("m"),
            tidal_error("m"),
        ];
        for payload in all {
            let obj = payload.as_object().expect("flat object");
            assert!(
                obj.values().all(|v| v.is_string() || v.is_null()),
                "all fields are strings or null: {payload}"
            );
            assert!(payload["state"].is_string());
            assert!(serde_json::to_string(&payload).is_ok());
        }
    }
}
