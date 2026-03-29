package com.medical.service;

import com.medical.entity.Patient;
import com.medical.repository.PatientRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
@RequiredArgsConstructor
public class PatientService {
    private final PatientRepository patientRepository;
    
    public List<Patient> getAllPatients() {
        return patientRepository.findAll();
    }
    
    public Patient getPatientById(Long id) {
        return patientRepository.findById(id);
    }
    
    public Patient createPatient(Patient patient) {
        patientRepository.insert(patient);
        return patient;
    }
    
    public Patient updatePatient(Patient patient) {
        patientRepository.update(patient);
        return patientRepository.findById(patient.getId());
    }
    
    public void deletePatient(Long id) {
        patientRepository.deleteById(id);
    }
}
