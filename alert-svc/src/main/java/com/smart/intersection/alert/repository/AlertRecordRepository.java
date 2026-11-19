package com.smart.intersection.alert.repository;

import com.smart.intersection.alert.entity.AlertRecordEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AlertRecordRepository extends JpaRepository<AlertRecordEntity, Long> {
    List<AlertRecordEntity> findByIntersectionIdOrderByCreatedAtDesc(String intersectionId);
    List<AlertRecordEntity> findByStatusOrderByCreatedAtDesc(String status);
}