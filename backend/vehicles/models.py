from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

User = get_user_model()

class VehicleType(models.Model):
    """Vehicle type classification"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    min_capacity = models.PositiveIntegerField(default=1)
    max_capacity = models.PositiveIntegerField(default=8)
    is_commercial = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vehicle_types'
        verbose_name = 'Vehicle Type'
        verbose_name_plural = 'Vehicle Types'
        
    def __str__(self):
        return self.name

class Vehicle(models.Model):
    """Vehicle model for fleet management"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
        ('suspended', 'Suspended'),
        ('decommissioned', 'Decommissioned'),
    ]
    
    FUEL_TYPE_CHOICES = [
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('cng', 'CNG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ]
    
    TRANSMISSION_CHOICES = [
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('semi_automatic', 'Semi-Automatic'),
    ]
    
    # Primary identifiers
    registration_number = models.CharField(
        max_length=15, 
        unique=True,
        validators=[RegexValidator(
            regex=r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$',
            message='Invalid registration number format'
        )]
    )
    vehicle_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Vehicle details
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE, related_name='vehicles')
    make = models.CharField(max_length=100)  # Toyota, Honda, etc.
    model = models.CharField(max_length=100)  # Camry, Civic, etc.
    year = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1990),
            MaxValueValidator(timezone.now().year + 1)
        ]
    )
    color = models.CharField(max_length=50)
    
    # Technical specifications
    engine_number = models.CharField(max_length=50, blank=True, null=True)
    chassis_number = models.CharField(max_length=50, unique=True)
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPE_CHOICES)
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    seating_capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    
    # Ownership and management
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='vehicles')
    owner_name = models.CharField(max_length=200)
    owner_phone = models.CharField(max_length=15)
    owner_address = models.TextField()
    
    # Status and operation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_vehicles')
    
    # Insurance and permits
    insurance_policy_number = models.CharField(max_length=100, blank=True, null=True)
    insurance_expiry = models.DateField(blank=True, null=True)
    permit_number = models.CharField(max_length=100, blank=True, null=True)
    permit_expiry = models.DateField(blank=True, null=True)
    
    # Operational data
    odometer_reading = models.PositiveIntegerField(default=0)  # in KM
    last_service_date = models.DateField(blank=True, null=True)
    next_service_due = models.DateField(blank=True, null=True)
    
    # Financial information
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    current_market_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    monthly_emi = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    
    # Timestamps
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_vehicles')
    
    class Meta:
        db_table = 'vehicles'
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
        ordering = ['-registered_at']
        indexes = [
            models.Index(fields=['registration_number']),
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['vehicle_type']),
        ]
        
    def __str__(self):
        return f"{self.registration_number} - {self.make} {self.model}"
    
    @property
    def is_insurance_expired(self):
        """Check if insurance is expired"""
        if self.insurance_expiry:
            return self.insurance_expiry < timezone.now().date()
        return True
    
    @property
    def is_permit_expired(self):
        """Check if permit is expired"""
        if self.permit_expiry:
            return self.permit_expiry < timezone.now().date()
        return True
    
    @property
    def is_service_due(self):
        """Check if service is due"""
        if self.next_service_due:
            return self.next_service_due <= timezone.now().date()
        return False

class VehicleDocument(models.Model):
    """Vehicle-related documents"""
    DOCUMENT_TYPE_CHOICES = [
        ('registration_certificate', 'Registration Certificate'),
        ('insurance_policy', 'Insurance Policy'),
        ('permit', 'Commercial Permit'),
        ('fitness_certificate', 'Fitness Certificate'),
        ('pollution_certificate', 'Pollution Certificate'),
        ('tax_receipt', 'Tax Receipt'),
        ('other', 'Other'),
    ]
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    document_number = models.CharField(max_length=100, blank=True, null=True)
    file = models.FileField(upload_to='vehicle_documents/')
    expiry_date = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_vehicle_docs')
    
    class Meta:
        db_table = 'vehicle_documents'
        unique_together = ['vehicle', 'document_type']
        
    def __str__(self):
        return f"{self.vehicle.registration_number} - {self.get_document_type_display()}"
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

class VehicleMaintenance(models.Model):
    """Vehicle maintenance records"""
    MAINTENANCE_TYPE_CHOICES = [
        ('routine', 'Routine Service'),
        ('repair', 'Repair'),
        ('breakdown', 'Breakdown'),
        ('accident', 'Accident Repair'),
        ('upgrade', 'Upgrade/Modification'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='maintenance_records')
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE_CHOICES)
    description = models.TextField()
    
    # Service provider details
    service_provider = models.CharField(max_length=200)
    service_provider_phone = models.CharField(max_length=15, blank=True, null=True)
    service_provider_address = models.TextField(blank=True, null=True)
    
    # Scheduling
    scheduled_date = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Costs
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Status and details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    odometer_reading = models.PositiveIntegerField(blank=True, null=True)
    parts_replaced = models.JSONField(default=list)  # List of parts/components
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicle_maintenance'
        verbose_name = 'Vehicle Maintenance'
        verbose_name_plural = 'Vehicle Maintenance Records'
        ordering = ['-scheduled_date']
        
    def __str__(self):
        return f"{self.vehicle.registration_number} - {self.get_maintenance_type_display()}"

class VehicleAssignment(models.Model):
    """Vehicle assignment to drivers"""
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='assignments')
    driver = models.ForeignKey('drivers.Driver', on_delete=models.CASCADE, related_name='vehicle_assignments')
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    unassigned_at = models.DateTimeField(null=True, blank=True)
    unassigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='vehicle_unassignments')
    
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'vehicle_assignments'
        verbose_name = 'Vehicle Assignment'
        verbose_name_plural = 'Vehicle Assignments'
        ordering = ['-assigned_at']
        
    def __str__(self):
        return f"{self.vehicle.registration_number} → {self.driver.user.get_full_name()}"

class VehicleInspection(models.Model):
    """Vehicle inspection records"""
    INSPECTION_TYPE_CHOICES = [
        ('pre_trip', 'Pre-Trip Inspection'),
        ('post_trip', 'Post-Trip Inspection'),
        ('routine', 'Routine Inspection'),
        ('safety', 'Safety Inspection'),
        ('compliance', 'Compliance Check'),
    ]
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='inspections')
    inspection_type = models.CharField(max_length=20, choices=INSPECTION_TYPE_CHOICES)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Inspection details
    inspection_date = models.DateTimeField(auto_now_add=True)
    odometer_reading = models.PositiveIntegerField()
    fuel_level = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])  # Percentage
    
    # Checklist (stored as JSON for flexibility)
    checklist_data = models.JSONField(default=dict)
    
    # Issues and notes
    issues_found = models.JSONField(default=list)
    notes = models.TextField(blank=True, null=True)
    photos = models.JSONField(default=list)  # Store photo URLs/paths
    
    # Status
    passed = models.BooleanField(default=True)
    requires_attention = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'vehicle_inspections'
        verbose_name = 'Vehicle Inspection'
        verbose_name_plural = 'Vehicle Inspections'
        ordering = ['-inspection_date']
        
    def __str__(self):
        return f"{self.vehicle.registration_number} - {self.get_inspection_type_display()}"
