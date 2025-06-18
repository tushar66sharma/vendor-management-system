from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

User = get_user_model()

class Driver(models.Model):
    """Driver model for driver management"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ]
    
    LICENSE_TYPE_CHOICES = [
        ('light_motor', 'Light Motor Vehicle'),
        ('heavy_motor', 'Heavy Motor Vehicle'),
        ('transport', 'Transport Vehicle'),
        ('motorcycle', 'Motorcycle'),
        ('commercial', 'Commercial Vehicle'),
    ]
    
    # Personal Information
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    driver_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    # Contact Information (additional to user model)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=15)
    emergency_contact_relationship = models.CharField(max_length=50)
    
    # Address Information
    permanent_address = models.TextField()
    permanent_city = models.CharField(max_length=100)
    permanent_state = models.CharField(max_length=100)
    permanent_postal_code = models.CharField(max_length=20)
    
    current_address = models.TextField(blank=True, null=True)
    current_city = models.CharField(max_length=100, blank=True, null=True)
    current_state = models.CharField(max_length=100, blank=True, null=True)
    current_postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Professional Information
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='drivers')
    date_of_joining = models.DateField()
    employment_type = models.CharField(
        max_length=20,
        choices=[
            ('full_time', 'Full Time'),
            ('part_time', 'Part Time'),
            ('contract', 'Contract'),
            ('freelance', 'Freelance'),
        ],
        default='full_time'
    )
    
    # License Information
    license_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(
            regex=r'^[A-Z]{2}[0-9]{2}[0-9]{11}$',
            message='Invalid license number format'
        )]
    )
    license_type = models.CharField(max_length=20, choices=LICENSE_TYPE_CHOICES)
    license_issue_date = models.DateField()
    license_expiry_date = models.DateField()
    license_issuing_authority = models.CharField(max_length=100)
    
    # Personal Details
    date_of_birth = models.DateField()
    blood_group = models.CharField(
        max_length=5,
        choices=[
            ('A+', 'A+'), ('A-', 'A-'),
            ('B+', 'B+'), ('B-', 'B-'),
            ('AB+', 'AB+'), ('AB-', 'AB-'),
            ('O+', 'O+'), ('O-', 'O-'),
        ],
        blank=True, null=True
    )
    
    # Physical attributes for verification
    height = models.PositiveIntegerField(blank=True, null=True, help_text='Height in cm')
    weight = models.PositiveIntegerField(blank=True, null=True, help_text='Weight in kg')
    
    # Experience and Skills
    years_of_experience = models.PositiveIntegerField(default=0)
    previous_companies = models.JSONField(default=list)  # List of previous employment
    specializations = models.JSONField(default=list)  # Special skills/certifications
    languages_known = models.JSONField(default=list)  # Languages spoken
    
    # Medical Information
    medical_certificate_number = models.CharField(max_length=100, blank=True, null=True)
    medical_certificate_expiry = models.DateField(blank=True, null=True)
    has_medical_conditions = models.BooleanField(default=False)
    medical_conditions = models.JSONField(default=list)  # List of medical conditions
    
    # Status and Verification
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_drivers')
    
    # Background Check
    background_check_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    background_check_date = models.DateField(blank=True, null=True)
    background_check_agency = models.CharField(max_length=200, blank=True, null=True)
    
    # Performance Metrics
    total_trips = models.PositiveIntegerField(default=0)
    total_distance_km = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_ratings = models.PositiveIntegerField(default=0)
    
    # Financial Information
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_branch = models.CharField(max_length=100, blank=True, null=True)
    ifsc_code = models.CharField(max_length=11, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_drivers')
    
    class Meta:
        db_table = 'drivers'
        verbose_name = 'Driver'
        verbose_name_plural = 'Drivers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['license_expiry_date']),
        ]
        
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.license_number})"
    
    @property
    def age(self):
        """Calculate driver's current age"""
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    @property
    def is_license_expired(self):
        """Check if driving license is expired"""
        return self.license_expiry_date < timezone.now().date()
    
    @property
    def is_medical_certificate_expired(self):
        """Check if medical certificate is expired"""
        if self.medical_certificate_expiry:
            return self.medical_certificate_expiry < timezone.now().date()
        return True
    
    @property
    def is_eligible_to_drive(self):
        """Check if driver is eligible to drive"""
        return (
            self.status == 'active' and
            self.is_verified and
            not self.is_license_expired and
            not self.is_medical_certificate_expired
        )

class DriverDocument(models.Model):
    """Driver-related documents"""
    DOCUMENT_TYPE_CHOICES = [
        ('driving_license', 'Driving License'),
        ('aadhar_card', 'Aadhar Card'),
        ('pan_card', 'PAN Card'),
        ('medical_certificate', 'Medical Certificate'),
        ('police_verification', 'Police Verification'),
        ('previous_experience', 'Previous Experience Letter'),
        ('education_certificate', 'Education Certificate'),
        ('training_certificate', 'Training Certificate'),
        ('photo', 'Passport Size Photo'),
        ('other', 'Other'),
    ]
    
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    document_number = models.CharField(max_length=100, blank=True, null=True)
    file = models.FileField(upload_to='driver_documents/')
    expiry_date = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_driver_docs')
    
    class Meta:
        db_table = 'driver_documents'
        unique_together = ['driver', 'document_type']
        
    def __str__(self):
        return f"{self.driver.user.get_full_name()} - {self.get_document_type_display()}"
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

class DriverTraining(models.Model):
    """Driver training records"""
    TRAINING_TYPE_CHOICES = [
        ('induction', 'Induction Training'),
        ('safety', 'Safety Training'),
        ('defensive_driving', 'Defensive Driving'),
        ('vehicle_maintenance', 'Vehicle Maintenance'),
        ('customer_service', 'Customer Service'),
        ('first_aid', 'First Aid'),
        ('refresher', 'Refresher Training'),
        ('specialized', 'Specialized Training'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='training_records')
    training_type = models.CharField(max_length=30, choices=TRAINING_TYPE_CHOICES)
    training_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Training provider
    training_provider = models.CharField(max_length=200)
    trainer_name = models.CharField(max_length=100, blank=True, null=True)
    trainer_contact = models.CharField(max_length=15, blank=True, null=True)
    
    # Schedule
    scheduled_date = models.DateTimeField()
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_hours = models.PositiveIntegerField(default=1)
    
    # Location
    training_location = models.CharField(max_length=200)
    training_address = models.TextField(blank=True, null=True)
    
    # Assessment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    certificate_number = models.CharField(max_length=100, blank=True, null=True)
    certificate_expiry = models.DateField(blank=True, null=True)
    
    # Notes and feedback
    trainer_notes = models.TextField(blank=True, null=True)
    driver_feedback = models.TextField(blank=True, null=True)
    
    # Costs
    training_cost = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'driver_training'
        verbose_name = 'Driver Training'
        verbose_name_plural = 'Driver Training Records'
        ordering = ['-scheduled_date']
        
    def __str__(self):
        return f"{self.driver.user.get_full_name()} - {self.training_name}"

class DriverPerformance(models.Model):
    """Driver performance tracking"""
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='performance_records')
    
    # Evaluation period
    evaluation_period_start = models.DateField()
    evaluation_period_end = models.DateField()
    
    # Performance metrics
    total_trips_completed = models.PositiveIntegerField(default=0)
    total_distance_covered = models.PositiveIntegerField(default=0)  # in KM
    total_hours_worked = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    
    # Ratings and feedback
    punctuality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    safety_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    customer_service_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    vehicle_maintenance_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    
    overall_rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    
    # Incidents and violations
    accidents_count = models.PositiveIntegerField(default=0)
    traffic_violations_count = models.PositiveIntegerField(default=0)
    customer_complaints_count = models.PositiveIntegerField(default=0)
    
    # Additional metrics
    fuel_efficiency_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    
    # Feedback
    supervisor_feedback = models.TextField(blank=True, null=True)
    improvement_areas = models.JSONField(default=list)
    achievements = models.JSONField(default=list)
    
    # Evaluation details
    evaluated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    evaluation_date = models.DateTimeField(auto_now_add=True)
    next_evaluation_due = models.DateField()
    
    class Meta:
        db_table = 'driver_performance'
        verbose_name = 'Driver Performance'
        verbose_name_plural = 'Driver Performance Records'
        ordering = ['-evaluation_date']
        unique_together = ['driver', 'evaluation_period_start', 'evaluation_period_end']
        
    def __str__(self):
        return f"{self.driver.user.get_full_name()} - Performance ({self.evaluation_period_start} to {self.evaluation_period_end})"

class DriverAttendance(models.Model):
    """Driver attendance tracking"""
    ATTENDANCE_STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
    ]
    
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS_CHOICES)
    
    # Time tracking
    check_in_time = models.TimeField(blank=True, null=True)
    check_out_time = models.TimeField(blank=True, null=True)
    break_duration_minutes = models.PositiveIntegerField(default=0)
    total_hours_worked = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    
    # Location tracking (optional)
    check_in_location = models.CharField(max_length=200, blank=True, null=True)
    check_out_location = models.CharField(max_length=200, blank=True, null=True)
    
    # Additional information
    notes = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'driver_attendance'
        verbose_name = 'Driver Attendance'
        verbose_name_plural = 'Driver Attendance Records'
        unique_together = ['driver', 'date']
        ordering = ['-date']
        
    def __str__(self):
        return f"{self.driver.user.get_full_name()} - {self.date} ({self.get_status_display()})"
