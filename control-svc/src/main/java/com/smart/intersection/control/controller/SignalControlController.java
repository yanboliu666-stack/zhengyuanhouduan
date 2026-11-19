package com.smart.intersection.control.controller;

import com.smart.intersection.control.dto.TimingCalculationReq;
import com.smart.intersection.control.dto.TimingResultDTO;
import com.smart.intersection.control.service.SignalControlService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/control")
public class SignalControlController {

    @Autowired
    private SignalControlService signalControlService;

    // 同时支持 /webster 和 /webster/calculate 两个路径
    @PostMapping(value = {"/webster", "/webster/calculate"})
    public ResponseEntity<TimingResultDTO> calculateWebster(@RequestBody(required = false) TimingCalculationReq req) {
        if (req == null) req = new TimingCalculationReq();
        return ResponseEntity.ok(signalControlService.calculateWebster(req));
    }

    @GetMapping(value = {"/webster", "/webster/calculate"})
    public ResponseEntity<TimingResultDTO> calculateWebsterGet(
            @RequestParam(value = "flows", required = false) List<Double> flows,
            @RequestParam(value = "lostTime", required = false, defaultValue = "12") Double lostTime) {

        TimingCalculationReq req = new TimingCalculationReq();
        req.setFlows(flows);
        req.setTotalLostTime(lostTime);
        return ResponseEntity.ok(signalControlService.calculateWebster(req));
    }
}