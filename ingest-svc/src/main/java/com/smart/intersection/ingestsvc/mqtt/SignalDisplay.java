package com.smart.intersection.ingestsvc.mqtt;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/** Read-only projection of mode A controller telemetry; never commands a lamp. */
public final class SignalDisplay {
    private SignalDisplay() {}
    private static final Map<String, String> PHASES = Map.of(
            "P_N", "north", "P_E", "east", "P_S", "south", "P_W", "west");

    public static Map<String, String> colors(String phase, String mode) {
        String active = PHASES.get(phase == null ? "" : phase.trim().toUpperCase(Locale.ROOT));
        boolean green = "normal".equalsIgnoreCase(mode);
        boolean yellow = "clearance".equalsIgnoreCase(mode);
        boolean known = "all_red".equalsIgnoreCase(mode) || (active != null && (green || yellow));
        Map<String, String> result = new HashMap<>();
        for (String dir : PHASES.values()) {
            String color = !known ? "unknown" : dir.equals(active) && green ? "green"
                                                : dir.equals(active) && yellow ? "yellow" : "red";
            result.put(dir, color);
            result.put(dir + "_through", color);
        }
        return result;
    }
}
