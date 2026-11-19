package com.smart.intersection.devicesvc.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.smart.intersection.common.Result;
import com.smart.intersection.devicesvc.entity.Device;
import com.smart.intersection.devicesvc.entity.Intersection;
import com.smart.intersection.devicesvc.entity.Lane;
import com.smart.intersection.devicesvc.mapper.DeviceMapper;
import com.smart.intersection.devicesvc.mapper.IntersectionMapper;
import com.smart.intersection.devicesvc.mapper.LaneMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;

@RestController
@RequestMapping("/api/v1/intersections")
public class IntersectionController {

    @Autowired
    private IntersectionMapper intersectionMapper;
    @Autowired
    private LaneMapper laneMapper;
    @Autowired
    private DeviceMapper deviceMapper;

    // 1. 查询所有路口
    @GetMapping
    public Result<List<Intersection>> list() {
        return Result.ok(intersectionMapper.selectList(null));
    }

    // 2. 根据ID获取路口详情
    @GetMapping("/{id}")
    public Result<Intersection> getById(@PathVariable String id) {
        Intersection i = intersectionMapper.selectById(id);
        return i != null ? Result.ok(i) : Result.fail(404, "路口不存在");
    }

    // 3. 新建路口
    @PostMapping
    public Result<?> create(@RequestBody Intersection intersection) {
        if (intersection.getId() == null) {
            return Result.fail(400, "路口ID不能为空");
        }
        intersection.setCreatedAt(LocalDateTime.now());
        intersection.setUpdatedAt(LocalDateTime.now());
        if (intersection.getStatus() == null) intersection.setStatus("ACTIVE");
        if (intersection.getControlMode() == null) intersection.setControlMode("WEBSTER");
        intersectionMapper.insert(intersection);
        return Result.ok(intersection);
    }

    // 4. 获取指定路口下的车道列表
    @GetMapping("/{id}/lanes")
    public Result<List<Lane>> getLanes(@PathVariable String id) {
        return Result.ok(laneMapper.selectList(
                new LambdaQueryWrapper<Lane>().eq(Lane::getIntersectionId, id)));
    }

    // 5. 为路口添加车道
    @PostMapping("/{id}/lanes")
    public Result<?> addLane(@PathVariable String id, @RequestBody Lane lane) {
        lane.setIntersectionId(id);
        lane.setCreatedAt(LocalDateTime.now());
        laneMapper.insert(lane);
        return Result.ok(lane);
    }

    // 6. 获取指定路口下的设备列表
    @GetMapping("/{id}/devices")
    public Result<List<Device>> getDevices(@PathVariable String id) {
        return Result.ok(deviceMapper.selectList(
                new LambdaQueryWrapper<Device>().eq(Device::getIntersectionId, id)));
    }
}