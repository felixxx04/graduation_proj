package com.grad.medrec.entity;

import com.grad.medrec.enumtype.PrivacyEventType;
import jakarta.persistence.*;

@Entity
@Table(name = "privacy_events")
public class PrivacyEvent extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private PrivacyEventType type;

    @Column(nullable = false)
    private Double epsilonSpent;

    @Column
    private Double deltaSpent;

    @Column(columnDefinition = "TEXT")
    private String note;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by")
    private UserAccount createdBy;

    public Long getId() {
        return id;
    }

    public PrivacyEventType getType() {
        return type;
    }

    public void setType(PrivacyEventType type) {
        this.type = type;
    }

    public Double getEpsilonSpent() {
        return epsilonSpent;
    }

    public void setEpsilonSpent(Double epsilonSpent) {
        this.epsilonSpent = epsilonSpent;
    }

    public Double getDeltaSpent() {
        return deltaSpent;
    }

    public void setDeltaSpent(Double deltaSpent) {
        this.deltaSpent = deltaSpent;
    }

    public String getNote() {
        return note;
    }

    public void setNote(String note) {
        this.note = note;
    }

    public UserAccount getCreatedBy() {
        return createdBy;
    }

    public void setCreatedBy(UserAccount createdBy) {
        this.createdBy = createdBy;
    }
}
