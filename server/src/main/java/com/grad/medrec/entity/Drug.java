package com.grad.medrec.entity;

import jakarta.persistence.*;

import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "drugs")
public class Drug extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 64)
    private String code;

    @Column(nullable = false, length = 128)
    private String name;

    @Column(nullable = false, length = 64)
    private String category;

    @Column(nullable = false, length = 64)
    private String typicalDosage;

    @Column(nullable = false, length = 128)
    private String typicalFrequency;

    @ElementCollection
    @CollectionTable(name = "drug_indications", joinColumns = @JoinColumn(name = "drug_id"))
    @Column(name = "item", nullable = false, length = 128)
    private List<String> indications = new ArrayList<>();

    @ElementCollection
    @CollectionTable(name = "drug_contraindications", joinColumns = @JoinColumn(name = "drug_id"))
    @Column(name = "item", nullable = false, length = 128)
    private List<String> contraindications = new ArrayList<>();

    @ElementCollection
    @CollectionTable(name = "drug_side_effects", joinColumns = @JoinColumn(name = "drug_id"))
    @Column(name = "item", nullable = false, length = 128)
    private List<String> commonSideEffects = new ArrayList<>();

    @ElementCollection
    @CollectionTable(name = "drug_interactions", joinColumns = @JoinColumn(name = "drug_id"))
    @Column(name = "item", nullable = false, length = 128)
    private List<String> interactionsWith = new ArrayList<>();

    public Long getId() {
        return id;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public String getTypicalDosage() {
        return typicalDosage;
    }

    public void setTypicalDosage(String typicalDosage) {
        this.typicalDosage = typicalDosage;
    }

    public String getTypicalFrequency() {
        return typicalFrequency;
    }

    public void setTypicalFrequency(String typicalFrequency) {
        this.typicalFrequency = typicalFrequency;
    }

    public List<String> getIndications() {
        return indications;
    }

    public void setIndications(List<String> indications) {
        this.indications = indications;
    }

    public List<String> getContraindications() {
        return contraindications;
    }

    public void setContraindications(List<String> contraindications) {
        this.contraindications = contraindications;
    }

    public List<String> getCommonSideEffects() {
        return commonSideEffects;
    }

    public void setCommonSideEffects(List<String> commonSideEffects) {
        this.commonSideEffects = commonSideEffects;
    }

    public List<String> getInteractionsWith() {
        return interactionsWith;
    }

    public void setInteractionsWith(List<String> interactionsWith) {
        this.interactionsWith = interactionsWith;
    }
}
