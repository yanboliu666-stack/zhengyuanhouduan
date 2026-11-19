package com.smart.intersection.control.repository;

import com.smart.intersection.control.entity.SignalPlanEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface SignalPlanRepository extends JpaRepository<SignalPlanEntity, Long> {
    List<SignalPlanEntity> findByIntersectionIdOrderByCreatedAtDesc(String intersectionId);
}