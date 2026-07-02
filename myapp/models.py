

from django.db import models
from django.contrib.auth.models import User


# -------------------------
# Book
# -------------------------
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    description = models.TextField()

    # Main/Cover Image
    cover_image = models.ImageField(upload_to='books/')

    actual_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2)

    stock = models.PositiveIntegerField(default=1)
    genre = models.CharField(max_length=100, default='General')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class BookImage(models.Model):
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='books/gallery/')

    def __str__(self):
        return f"{self.book.title} Image"
# -------------------------
# Address
# -------------------------

class Address(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    fullname = models.CharField(max_length=100)

    phone = models.CharField(max_length=15)

    house = models.CharField(max_length=200)

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    pincode = models.CharField(max_length=10)

    def __str__(self):
        return self.fullname


# -------------------------
# Cart
# -------------------------
class Cart(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


# -------------------------
# Cart Item
# -------------------------
class CartItem(models.Model):

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)

    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.book.discount_price * self.quantity

    def __str__(self):
        return self.book.title


# -------------------------
# Order
# -------------------------
class Order(models.Model):

    STATUS = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    address = models.ForeignKey(Address, on_delete=models.CASCADE)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20,
                              choices=STATUS,
                              default='Pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Order " + str(self.id)


# -------------------------
# Order Item
# -------------------------
class OrderItem(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField()

    price = models.DecimalField(max_digits=10,
                                decimal_places=2)

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return self.book.title


# -------------------------
# Payment
# -------------------------
# -------------------------
# Payment
# -------------------------
class Payment(models.Model):

    STATUS = (
        ('Pending', 'Pending'),
        ('Success', 'Success'),
        ('Failed', 'Failed'),
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        null=True,  # Allow null
        blank=True  # Allow blank in forms
    )

    razorpay_order_id = models.CharField(max_length=200)

    razorpay_payment_id = models.CharField(max_length=200,
                                           blank=True,
                                           null=True)

    razorpay_signature = models.CharField(max_length=300,
                                          blank=True,
                                          null=True)

    amount = models.DecimalField(max_digits=10,
                                 decimal_places=2)

    status = models.CharField(max_length=20,
                              choices=STATUS,
                              default='Pending')

    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.razorpay_order_id
    


# -------------------------
# Wishlist
# -------------------------
class Wishlist(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist'
    )

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"