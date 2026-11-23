package com.smart.intersection.ingestsvc.controller;

import java.util.*;

/** Public, read-only site metadata. Configuration never dispatches signals. */
public final class PananSite {
    private PananSite() {}
    public static Map<String,Object> attach(Map<String,Object> state, String id, String sourceId,
                                            String binding, boolean surveyed, long now) {
        state.put("server_ms",now);
        if (!sourceId.equals(id)) return state;
        List<String> arms=Arrays.asList(binding.trim().toUpperCase(Locale.ROOT).split("\\s*,\\s*",-1));
        boolean valid=new HashSet<>(arms).equals(Set.of("P_N","P_E","P_S","P_W")) && arms.size()==4;
        state.put("site", Map.of("id","panan_nanhuan_shuangxi", "name","南环路与双溪路交叉口",
                "binding", valid?arms:List.of(), "confirmed",valid && surveyed));
        // Previous deployment may have only traffic_ts and lanes. Restore perception,
        // never infer a green from an old backend's default mode=normal or last_updated.
        if (!(state.get("edge_feed") instanceof Map) && state.get("traffic_ts") instanceof Number) {
            Map<String,Object> legacy=new HashMap<>();legacy.put("ts",state.get("traffic_ts"));
            for(String k:List.of("lanes","degradation")) if(state.containsKey(k)) legacy.put(k,state.get(k));
            if(state.get("board_frame") instanceof Map) legacy.put("board",state.get("board_frame"));
            legacy.put("phase",state.get("current_phase_id"));legacy.put("legacy",true);state.put("edge_feed",legacy);
        }
        return state;
    }
}
