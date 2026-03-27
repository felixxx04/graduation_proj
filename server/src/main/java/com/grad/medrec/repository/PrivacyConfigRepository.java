package com.grad.medrec.repository;

import com.grad.medrec.entity.PrivacyConfig;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PrivacyConfigRepository extends JpaRepository<PrivacyConfig, Long> {
}
