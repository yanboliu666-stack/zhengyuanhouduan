package com.smart.intersection.control.service;

import com.smart.intersection.control.dto.FuzzyAdjustmentReq;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Component
public class FuzzyControlEngine {

    /**
     * 基于排队长度与到达率推理绿灯延长时长
     */
    public Map<String, Object> evaluateGreenExtension(FuzzyAdjustmentReq req) {
        int queue = req.getQueueLength() != null ? req.getQueueLength() : 0;
        int arrival = req.getArrivalRate() != null ? req.getArrivalRate() : 0;

        int extensionSeconds = 0;
        String action = "TERMINATE";

        if (queue > 8 && arrival < 5) {
            extensionSeconds = 6;
            action = "EXTEND";
        } else if (queue >= 3 && queue <= 8) {
            extensionSeconds = 3;
            action = "EXTEND";
        } else {
            extensionSeconds = 0;
            action = "TERMINATE";
        }

        // 最大绿灯时长保护 (60s)
        if (req.getCurrentGreenTime() + extensionSeconds > 60) {
            extensionSeconds = 0;
            action = "FORCE_TERMINATE";
        }

        Map<String, Object> result = new HashMap<>();
        result.put("intersectionId", req.getIntersectionId());
        result.put("currentPhase", req.getCurrentPhase());
        result.put("action", action);
        result.put("extensionSeconds", extensionSeconds);
        result.put("recommendedGreenTime", req.getCurrentGreenTime() + extensionSeconds);
        return result;
    }
}