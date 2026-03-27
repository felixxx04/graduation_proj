package com.grad.medrec.repository;

import com.grad.medrec.entity.PrivacyEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface PrivacyEventRepository extends JpaRepository<PrivacyEvent, Long> {

    @Query("select coalesce(sum(e.epsilonSpent), 0) from PrivacyEvent e")
    double sumEpsilonSpent();
}
