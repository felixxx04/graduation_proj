package com.grad.medrec.entity;

import com.grad.medrec.enumtype.ApplicationStage;
import com.grad.medrec.enumtype.NoiseMechanism;
import jakarta.persistence.*;

@Entity
@Table(name = "privacy_configs")
public class PrivacyConfig extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Double epsilon;

    @Column(nullable = false)
    private Double deltaValue;

    @Column(nullable = false)
    private Double sensitivity;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private NoiseMechanism noiseMechanism;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private ApplicationStage applicationStage;

    @Column(nullable = false)
    private Double privacyBudget;

    public Long getId() {
        return id;
    }

    public Double getEpsilon() {
        return epsilon;
    }

    public void setEpsilon(Double epsilon) {
        this.epsilon = epsilon;
    }

    public Double getDeltaValue() {
        return deltaValue;
    }

    public void setDeltaValue(Double deltaValue) {
        this.deltaValue = deltaValue;
    }

    public Double getSensitivity() {
        return sensitivity;
    }

    public void setSensitivity(Double sensitivity) {
        this.sensitivity = sensitivity;
    }

    public NoiseMechanism getNoiseMechanism() {
        return noiseMechanism;
    }

    public void setNoiseMechanism(NoiseMechanism noiseMechanism) {
        this.noiseMechanism = noiseMechanism;
    }

    public ApplicationStage getApplicationStage() {
        return applicationStage;
    }

    public void setApplicationStage(ApplicationStage applicationStage) {
        this.applicationStage = applicationStage;
    }

    public Double getPrivacyBudget() {
        return privacyBudget;
    }

    public void setPrivacyBudget(Double privacyBudget) {
        this.privacyBudget = privacyBudget;
    }
}
