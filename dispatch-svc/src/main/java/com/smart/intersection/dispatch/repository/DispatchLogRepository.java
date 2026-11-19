package com.smart.intersection.dispatch.repository;

import com.smart.intersection.dispatch.entity.DispatchLogEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface DispatchLogRepository extends JpaRepository<DispatchLogEntity, Long> {
}