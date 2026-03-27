package com.grad.medrec.repository;

import com.grad.medrec.entity.TrainingRun;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TrainingRunRepository extends JpaRepository<TrainingRun, Long> {
}
