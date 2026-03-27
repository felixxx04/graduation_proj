package com.grad.medrec.repository;

import com.grad.medrec.entity.TrainingEpoch;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TrainingEpochRepository extends JpaRepository<TrainingEpoch, Long> {
}
