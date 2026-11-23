package com.smart.intersection.ingestsvc.mqtt;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

/** Monitor-only event projection. SOURCE time is not refreshed by unrelated MQTT traffic. */
public final class EdgeFeed {
    private EdgeFeed() {}
    public static void accept(ObjectNode parent, String kind, JsonNode payload, long arrived) {
        double ts = payload.path("ts_wall").asDouble(0);
        if (!Double.isFinite(ts) || ts <= 0) return;
        ObjectNode s = parent.with("edge_feed");
        if (kind.equals("traffic_state")) {
            double prev = s.path("ts").asDouble(0);
            if (ts <= prev) return; // replay/duplicate, not a heartbeat
            // Do not carry a previous session's mode over a telemetry outage. A mode
            // event received just before this sample is still valid evidence.
            if (prev > 0 && ts-prev >= 4 && s.path("mode_ts").asDouble() < ts-4) s.remove("mode");
            s.put("interval_ms", prev > 0 ? Math.round((ts-prev)*1000) : 0);
            s.put("seq", s.path("seq").asLong()+1);
            s.put("ts",ts); s.put("received_ms",arrived);
            s.put("phase",payload.path("current_phase_id").asText(""));
            s.set("lanes",payload.path("lanes").isObject()?payload.get("lanes"):s.objectNode());
            s.put("degradation",payload.path("degradation").asText("unknown"));
            if (payload.path("mode").isTextual() && ts >= s.path("mode_ts").asDouble()) {
                s.put("mode",payload.get("mode").asText()); s.put("mode_ts",ts);
            }
            if(payload.path("board_frame").isObject()) s.set("board",payload.get("board_frame")); else s.remove("board");
            if (ts + 0.05 >= s.path("mode_ts").asDouble()) s.put("await_phase",false);
            return;
        }
        if (kind.equals("mode_change")) {
            if (ts <= s.path("mode_ts").asDouble()) return;
            s.put("mode_ts",ts); s.put("mode",payload.path("to_mode").asText("unknown"));
            if ("normal".equals(s.path("mode").asText()) && ts>s.path("ts").asDouble()) s.put("await_phase",true);
        }
        if (!(kind.equals("mode_change") || kind.equals("decision_change") || kind.equals("degradation_change") || kind.equals("heartbeat_fault") || kind.equals("feedback_failure") || kind.equals("alarm"))) return;
        ArrayNode events=s.withArray("events");
        for(JsonNode e:events) if(e.path("type").asText().equals(kind)&&e.path("ts").asDouble()==ts)return;
        ObjectNode event=s.objectNode(); event.put("type",kind); event.put("ts",ts);
        if(payload.hasNonNull("tick_id"))event.set("tick",payload.get("tick_id"));
        for(String name:new String[]{"to_phase","from_phase","from_mode","to_mode","alarm_type","reason"}) if(payload.hasNonNull(name))event.set(name,payload.get(name));
        events.insert(0,event);if(events.size()>24)events.remove(24);
    }
}
