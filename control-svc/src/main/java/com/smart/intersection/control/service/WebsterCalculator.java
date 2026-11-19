package com.smart.intersection.control.service;

import org.springframework.stereotype.Component;
import java.util.*;

@Component
public class WebsterCalculator {

    public Map<String, Object> calculate(List<Integer> flows, Integer totalLostTime) {
        if (flows == null || flows.isEmpty()) {
            throw new IllegalArgumentException("相位流量数据不能为空");
        }

        // 假设饱和流量为 1800 pcu/h
        double saturationFlow = 1800.0;
        double sumY = 0;
        List<Double> yValues = new ArrayList<>();

        for (Integer flow : flows) {
            double y = flow / saturationFlow;
            yValues.add(y);
            sumY += y;
        }

        // Webster 最优周期公式: C = (1.5L + 5) / (1 - Y)
        if (sumY >= 1.0) sumY = 0.9; // 防止分母为0或负数
        int optCycle = (int) Math.round((1.5 * totalLostTime + 5) / (1 - sumY));

        // 限制周期在 40s - 180s 之间
        optCycle = Math.max(40, Math.min(180, optCycle));

        // 计算各个相位的绿灯时间分配
        List<Integer> greenTimes = new ArrayList<>();
        int totalGreenTime = optCycle - totalLostTime;

        for (double y : yValues) {
            int g = (int) Math.round(totalGreenTime * (y / sumY));
            greenTimes.add(g);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("optCycle", optCycle);
        result.put("greenTimes", greenTimes);
        return result;
    }
}