from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()

class Vendor(models.Model):
    """Vendor model implementing Nested Set Model for hierarchy"""
    VENDOR_TYPE_CHOICES = [
        ('super_vendor', 'Super Vendor'),
        ('regional_vendor', 'Regional Vendor'),
        ('city_vendor', 'City Vendor'),
        ('local_vendor', 'Local Vendor'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('pending', 'Pending Approval'),
    ]
    
    name = models.CharField(max_length=200)
    vendor_type = models.CharField(max_length=20, choices=VENDOR_TYPE_CHOICES)
    code = models.CharField(max_length=50, unique=True)  # Unique vendor code
    
    # Nested Set Model fields for hierarchy (O(1) complexity)
    lft = models.PositiveIntegerField(default=0, db_index=True)
    rght = models.PositiveIntegerField(default=0, db_index=True)
    level = models.PositiveIntegerField(default=0, db_index=True)
    
    # Hierarchy relationship
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Vendor details
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_vendors')
    admin_users = models.ManyToManyField(User, through='VendorAdmin', related_name='managed_vendors')
    
    # Contact information
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    website = models.URLField(blank=True, null=True)
    
    # Address information
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    
    # Business information
    business_license = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Status and permissions
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    # Operational limits
    max_vehicles = models.PositiveIntegerField(default=10)
    max_drivers = models.PositiveIntegerField(default=10)
    max_sub_vendors = models.PositiveIntegerField(default=5)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vendors'
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        ordering = ['lft']
        indexes = [
            models.Index(fields=['lft', 'rght']),
            models.Index(fields=['level']),
            models.Index(fields=['vendor_type']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"{self.name} ({self.get_vendor_type_display()})"
    
    def get_ancestors(self):
        """Get all ancestor vendors"""
        return Vendor.objects.filter(lft__lt=self.lft, rght__gt=self.rght).order_by('lft')
    
    def get_descendants(self):
        """Get all descendant vendors"""
        return Vendor.objects.filter(lft__gt=self.lft, rght__lt=self.rght).order_by('lft')
    
    def get_children(self):
        """Get direct children vendors"""
        return Vendor.objects.filter(parent=self).order_by('lft')
    
    def is_ancestor_of(self, other):
        """Check if this vendor is ancestor of another"""
        return self.lft < other.lft and self.rght > other.rght
    
    def is_descendant_of(self, other):
        """Check if this vendor is descendant of another"""
        return self.lft > other.lft and self.rght < other.rght

class VendorAdmin(models.Model):
    """Through model for vendor admin relationships"""
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='admin')
    permissions = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='vendor_assignments')
    
    class Meta:
        db_table = 'vendor_admins'
        unique_together = ['vendor', 'user']
        
    def __str__(self):
        return f"{self.user.email} - {self.vendor.name}"

class Permission(models.Model):
    """System permissions for role-based access control"""
    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    module = models.CharField(max_length=50)  # accounts, vendors, vehicles, etc.
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'permissions'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        
    def __str__(self):
        return f"{self.name} ({self.module})"

class VendorPermission(models.Model):
    """Vendor-specific permissions and delegation"""
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='granted_permissions')
    
    # Delegation options
    can_delegate = models.BooleanField(default=False)
    is_temporary = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Scope limitations
    scope_data = models.JSONField(default=dict)  # Additional scope restrictions
    
    is_active = models.BooleanField(default=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vendor_permissions'
        unique_together = ['vendor', 'user', 'permission']
        
    def __str__(self):
        return f"{self.user.email} - {self.permission.name} on {self.vendor.name}"
    
    def is_expired(self):
        """Check if permission is expired"""
        if self.is_temporary and self.expires_at:
            return timezone.now() > self.expires_at
        return False

class VendorSettings(models.Model):
    """Vendor-specific configuration settings"""
    vendor = models.OneToOneField(Vendor, on_delete=models.CASCADE, related_name='settings')
    
    # Operational settings
    allow_vehicle_self_registration = models.BooleanField(default=False)
    allow_driver_self_registration = models.BooleanField(default=False)
    require_document_verification = models.BooleanField(default=True)
    auto_approve_vehicles = models.BooleanField(default=False)
    auto_approve_drivers = models.BooleanField(default=False)
    
    # Notification settings
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    notification_emails = models.JSONField(default=list)  # Additional notification emails
    
    # Business hours
    business_hours = models.JSONField(default=dict)  # Store business hours as JSON
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    
    # Limits and quotas
    monthly_vehicle_limit = models.PositiveIntegerField(null=True, blank=True)
    monthly_driver_limit = models.PositiveIntegerField(null=True, blank=True)
    storage_limit_mb = models.PositiveIntegerField(default=1000)  # Document storage limit
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vendor_settings'
        verbose_name = 'Vendor Settings'
        verbose_name_plural = 'Vendor Settings'
        
    def __str__(self):
        return f"Settings for {self.vendor.name}"
