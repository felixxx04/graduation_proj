package com.grad.medrec.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "training_epochs")
public class TrainingEpoch extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "training_run_id", nullable = false)
    private TrainingRun trainingRun;

    @Column(nullable = false)
    private Integer epochIndex;

    @Column(nullable = false)
    private Double loss;

    @Column(nullable = false)
    private Double accuracy;

    @Column(nullable = false)
    private Double epsilonSpent;

    public Long getId() {
        return id;
    }

    public TrainingRun getTrainingRun() {
        return trainingRun;
    }

    public void setTrainingRun(TrainingRun trainingRun) {
        this.trainingRun = trainingRun;
    }

    public Integer getEpochIndex() {
        return epochIndex;
    }

    public void setEpochIndex(Integer epochIndex) {
        this.epochIndex = epochIndex;
    }

    public Double getLoss() {
        return loss;
    }

    public void setLoss(Double loss) {
        this.loss = loss;
    }

    public Double getAccuracy() {
        return accuracy;
    }

    public void setAccuracy(Double accuracy) {
        this.accuracy = accuracy;
    }

    public Double getEpsilonSpent() {
        return epsilonSpent;
    }

    public void setEpsilonSpent(Double epsilonSpent) {
        this.epsilonSpent = epsilonSpent;
    }
}
