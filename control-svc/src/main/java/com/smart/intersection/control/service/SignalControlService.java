package com.smart.intersection.control.service;

import com.smart.intersection.control.dto.TimingCalculationReq;
import com.smart.intersection.control.dto.TimingResultDTO;
import org.springframework.stereotype.Service;
import java.util.ArrayList;
import java.util.List;

@Service
public class SignalControlService {

    public TimingResultDTO calculateWebster(TimingCalculationReq req) {
        // 1. 获取参数
        List<Double> flowList = req.extractFlowList();
        double lostTime = (req.getTotalLostTime() != null) ? req.getTotalLostTime() : 12.0;
        double satFlow = (req.getSaturationFlow() != null) ? req.getSaturationFlow() : 1800.0;

        // 2. 计算流量比
        double sumY = 0.0;
        List<Double> yList = new ArrayList<>();
        for (Double f : flowList) {
            double y = f / satFlow;
            yList.add(y);
            sumY += y;
        }

        // 3. 安全保护
        if (sumY >= 0.9) sumY = 0.9;
        if (sumY <= 0.1) sumY = 0.1;

        // 4. Webster 公式: C = (1.5L + 5) / (1 - Y)
        int cycle = (int) Math.round((1.5 * lostTime + 5) / (1 - sumY));
        if (cycle < 40) cycle = 40;
        if (cycle > 180) cycle = 180;

        // 5. 分配绿灯
        double totalGreen = cycle - lostTime;
        List<Integer> greens = new ArrayList<>();
        for (Double y : yList) {
            int g = (int) Math.round(totalGreen * (y / sumY));
            greens.add(Math.max(g, 7));
        }

        return TimingResultDTO.builder()
                .cycleLength(cycle)
                .totalLostTime(lostTime)
                .flowRatioSum(Math.round(sumY * 100.0) / 100.0)
                .greenTimes(greens)
                .build();
    }
}