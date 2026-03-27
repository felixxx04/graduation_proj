package com.grad.medrec.entity;

import com.grad.medrec.enumtype.TrainingRunStatus;
import jakarta.persistence.*;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "training_runs")
public class TrainingRun extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by")
    private UserAccount createdBy;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private TrainingRunStatus status;

    @Column(nullable = false)
    private Integer totalEpochs;

    @Column(nullable = false)
    private Double epsilonPerEpoch;

    @Column(nullable = false)
    private LocalDateTime startedAt;

    @Column
    private LocalDateTime finishedAt;

    @OneToMany(mappedBy = "trainingRun", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<TrainingEpoch> epochs = new ArrayList<>();

    public Long getId() {
        return id;
    }

    public UserAccount getCreatedBy() {
        return createdBy;
    }

    public void setCreatedBy(UserAccount createdBy) {
        this.createdBy = createdBy;
    }

    public TrainingRunStatus getStatus() {
        return status;
    }

    public void setStatus(TrainingRunStatus status) {
        this.status = status;
    }

    public Integer getTotalEpochs() {
        return totalEpochs;
    }

    public void setTotalEpochs(Integer totalEpochs) {
        this.totalEpochs = totalEpochs;
    }

    public Double getEpsilonPerEpoch() {
        return epsilonPerEpoch;
    }

    public void setEpsilonPerEpoch(Double epsilonPerEpoch) {
        this.epsilonPerEpoch = epsilonPerEpoch;
    }

    public LocalDateTime getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(LocalDateTime startedAt) {
        this.startedAt = startedAt;
    }

    public LocalDateTime getFinishedAt() {
        return finishedAt;
    }

    public void setFinishedAt(LocalDateTime finishedAt) {
        this.finishedAt = finishedAt;
    }

    public List<TrainingEpoch> getEpochs() {
        return epochs;
    }

    public void setEpochs(List<TrainingEpoch> epochs) {
        this.epochs = epochs;
    }
}
