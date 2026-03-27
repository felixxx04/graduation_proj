package com.grad.medrec.entity;

import com.grad.medrec.enumtype.ApplicationStage;
import com.grad.medrec.enumtype.NoiseMechanism;
import jakarta.persistence.*;

import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "recommendations")
public class Recommendation extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "patient_id")
    private Patient patient;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by")
    private UserAccount createdBy;

    @Column
    private Integer age;

    @Column(length = 16)
    private String gender;

    @Column(columnDefinition = "TEXT")
    private String diseases;

    @Column(columnDefinition = "TEXT")
    private String symptoms;

    @Column(columnDefinition = "TEXT")
    private String allergies;

    @Column(columnDefinition = "TEXT")
    private String currentMedications;

    @Column(nullable = false)
    private Boolean dpEnabled;

    @Column
    private Double epsilonUsed;

    @Enumerated(EnumType.STRING)
    @Column(length = 16)
    private NoiseMechanism noiseMechanism;

    @Enumerated(EnumType.STRING)
    @Column(length = 16)
    private ApplicationStage applicationStage;

    @OneToMany(mappedBy = "recommendation", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<RecommendationItem> items = new ArrayList<>();

    public Long getId() {
        return id;
    }

    public Patient getPatient() {
        return patient;
    }

    public void setPatient(Patient patient) {
        this.patient = patient;
    }

    public UserAccount getCreatedBy() {
        return createdBy;
    }

    public void setCreatedBy(UserAccount createdBy) {
        this.createdBy = createdBy;
    }

    public Integer getAge() {
        return age;
    }

    public void setAge(Integer age) {
        this.age = age;
    }

    public String getGender() {
        return gender;
    }

    public void setGender(String gender) {
        this.gender = gender;
    }

    public String getDiseases() {
        return diseases;
    }

    public void setDiseases(String diseases) {
        this.diseases = diseases;
    }

    public String getSymptoms() {
        return symptoms;
    }

    public void setSymptoms(String symptoms) {
        this.symptoms = symptoms;
    }

    public String getAllergies() {
        return allergies;
    }

    public void setAllergies(String allergies) {
        this.allergies = allergies;
    }

    public String getCurrentMedications() {
        return currentMedications;
    }

    public void setCurrentMedications(String currentMedications) {
        this.currentMedications = currentMedications;
    }

    public Boolean getDpEnabled() {
        return dpEnabled;
    }

    public void setDpEnabled(Boolean dpEnabled) {
        this.dpEnabled = dpEnabled;
    }

    public Double getEpsilonUsed() {
        return epsilonUsed;
    }

    public void setEpsilonUsed(Double epsilonUsed) {
        this.epsilonUsed = epsilonUsed;
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

    public List<RecommendationItem> getItems() {
        return items;
    }

    public void setItems(List<RecommendationItem> items) {
        this.items = items;
    }
}
