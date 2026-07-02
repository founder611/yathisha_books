import time
from django.shortcuts import render, get_object_or_404
from django.core.files.storage import FileSystemStorage
from django.shortcuts import redirect
from django.db.models import Sum, Count
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from myapp.models import *
import razorpay
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt



#admin 

def admin_login_get(request):
    return render(request,'admin/adminlogin.html')

def admin_login_post(request):
    username=request.POST['username']
    password=request.POST['password']
    user=authenticate(username=username,password=password)
    if user is not None:
        login(request,user)
        if user.is_superuser:
            return redirect('/myapp/dashboard')
        else:
            return HttpResponse('''<script>alert('Invalid credentials');window.location='/myapp/admin_login_get/'</script>''')
    else:
        return HttpResponse('''<script>alert('Invalid credentials');window.location='/myapp/admin_login_get/'</script>''')



def admin_logout(request):
    logout(request)
    return redirect('/myapp/admin_login_get/')




def dashboard(request):
    total_books = Book.objects.count()
    total_stock = Book.objects.aggregate(total=Sum('stock'))['total'] or 0
    low_stock_books = Book.objects.filter(stock__lte=5).order_by('stock')
    out_of_stock = Book.objects.filter(stock=0).count()
    recent_books = Book.objects.order_by('-id')[:5]

    context = {
        'total_books': total_books,
        'total_stock': total_stock,
        'low_stock_count': low_stock_books.count(),
        'low_stock_books': low_stock_books[:5],
        'out_of_stock': out_of_stock,
        'recent_books': recent_books,
    }
    return render(request, 'admin/dashboard.html', context)



def addbook_get(request):
    return render(request,'admin/add_book.html')


def addbook_post(request):
    if request.method == "POST":

        title = request.POST['title']
        author = request.POST['author']
        description = request.POST['description']
        actual_price = request.POST['actual_price']
        discount_price = request.POST['discount_price']
        genre = request.POST['genre']
        stock = request.POST['stock']

        fs = FileSystemStorage()

        # Save cover image
        cover = request.FILES['cover_image']
        cover_name = fs.save(cover.name, cover)

        # Create book
        book = Book.objects.create(
            title=title,
            author=author,
            description=description,
            cover_image=cover_name,
            genre=genre,
            actual_price=actual_price,
            discount_price=discount_price,
            stock=stock,
        )

        # Save multiple gallery images
        gallery_images = request.FILES.getlist("gallery_images")

        for img in gallery_images:
            img_name = fs.save(img.name, img)

            BookImage.objects.create(
                book=book,
                image=img_name
            )

        return redirect("/myapp/dashboard/")   # Change to your URL name

    return redirect("/myapp/dashboard/")


def view_books(request):
    books = Book.objects.prefetch_related('images').all().order_by('-id')
    return render(request, "admin/viewbooks.html", {"books": books})


def book_gallery(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    context = {
        "book": book,
        "images": book.images.all()
    }

    return render(request, "admin/view_gallery.html", context)




def edit_book(request, book_id):

    book = get_object_or_404(Book, id=book_id)

    if request.method == "POST":

        book.title = request.POST['title']
        book.author = request.POST['author']
        book.description = request.POST['description']
        book.actual_price = request.POST['actual_price']
        book.discount_price = request.POST['discount_price']
        book.stock = request.POST['stock']
        book.genre = request.POST['genre']

        fs = FileSystemStorage()

        # Update cover image (optional)
        if 'cover_image' in request.FILES:

            cover = request.FILES['cover_image']
            filename = fs.save(cover.name, cover)
            book.cover_image = filename

        book.save()

        # Add new gallery images (optional)
        images = request.FILES.getlist("gallery_images")

        for img in images:

            filename = fs.save(img.name, img)

            BookImage.objects.create(
                book=book,
                image=filename
            )

        return redirect("/myapp/view_books/")

    return render(request, "admin/edit_book.html", {
        "book": book
    })


def delete_book(request,id):
    Book.objects.get(id=id).delete()
    return redirect('/myapp/view_books/')


#user views

def user_homepage(request):

    genre = request.GET.get('genre')

    if genre:
        books = Book.objects.filter(genre=genre).order_by('-id')
    else:
        books = Book.objects.all().order_by('-id')

    genres = Book.objects.values_list('genre', flat=True).distinct()
    latest_books = Book.objects.all().order_by('-id')[:7]

    cart_count = 0
    total = 0

    wishlist_count = Wishlist.objects.filter(
    user=request.user
    ).count()

    if request.user.is_authenticated:

        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_items = CartItem.objects.filter(cart=cart)

        cart_count = cart_items.count()   # Number of different books

        total = sum(item.subtotal() for item in cart_items)

    return render(request, 'user/user_homepage.html', {
        'books': books,
        'genres': genres,
        'selected_genre': genre,
        'latest_books': latest_books,
        'cart_count': cart_count,
        'total': total,
        'wishlist_count': wishlist_count,
    })



def user_view_book_details(request, id):
    book = get_object_or_404(Book, id=id)
    
    book_images = BookImage.objects.filter(book=book)
    
    related_books = Book.objects.filter(
        genre=book.genre
    ).exclude(id=book.id)[:4]
    
    context = {
        'book': book,
        'book_images': book_images,
        'related_books': related_books,
    }
    return render(request, 'user/bookdetails.html', context)




from django.http import JsonResponse

@login_required
def view_cart(request):
    """View the user's cart - returns JSON for AJAX or HTML for full page"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('book')
    
    total = sum(item.subtotal() for item in cart_items)
    cart_count = cart_items.count()
    
    # If AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        items_data = []
        for item in cart_items:
            items_data.append({
                'id': item.id,
                'book_id': item.book.id,
                'title': item.book.title,
                'genre': item.book.genre,
                'price': float(item.book.discount_price or item.book.actual_price),
                'image': item.book.cover_image.url,
                'quantity': item.quantity,
            })
        
        return JsonResponse({
            'success': True,
            'cart_count': cart_count,
            'cart_total': float(total),
            'cart_items': items_data,
        })
    
    # Regular HTML response
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_count,
    }
    return render(request, 'user/cart.html', context)


@login_required
def add_to_cart(request, book_id):
    """Add a book to the user's cart"""
    book = get_object_or_404(Book, id=book_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        book=book,
        defaults={'quantity': 1}
    )
    
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
    
    # Get updated cart data
    cart_items = CartItem.objects.filter(cart=cart).select_related('book')
    total = sum(item.subtotal() for item in cart_items)
    cart_count = cart_items.count()
    
    # If AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        items_data = []
        for item in cart_items:
            items_data.append({
                'id': item.id,
                'book_id': item.book.id,
                'title': item.book.title,
                'genre': item.book.genre,
                'price': float(item.book.discount_price or item.book.actual_price),
                'image': item.book.cover_image.url,
                'quantity': item.quantity,
            })
        
        return JsonResponse({
            'success': True,
            'message': f'"{book.title}" added to cart!',
            'cart_count': cart_count,
            'cart_total': float(total),
            'cart_items': items_data,
        })
    
    # Regular redirect
    messages.success(request, f'"{book.title}" added to your cart!')
    next_url = request.META.get('HTTP_REFERER', '/myapp/user_homepage/')
    return redirect(next_url)


@login_required
def remove_from_cart(request, item_id):
    """Remove an item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    
    # Get updated cart data
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('book')
    total = sum(item.subtotal() for item in cart_items)
    cart_count = cart_items.count()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        items_data = []
        for item in cart_items:
            items_data.append({
                'id': item.id,
                'book_id': item.book.id,
                'title': item.book.title,
                'genre': item.book.genre,
                'price': float(item.book.discount_price or item.book.actual_price),
                'image': item.book.cover_image.url,
                'quantity': item.quantity,
            })
        
        return JsonResponse({
            'success': True,
            'cart_count': cart_count,
            'cart_total': float(total),
            'cart_items': items_data,
        })
    
    messages.success(request, 'Item removed from cart!')
    return redirect('view_cart')


@login_required
def update_cart_item(request, item_id):
    """Update quantity of a cart item"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    action = request.GET.get('action', 'increase')
    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease':
        cart_item.quantity -= 1
        if cart_item.quantity < 1:
            cart_item.delete()
    cart_item.save()
    
    # Get updated cart data
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('book')
    total = sum(item.subtotal() for item in cart_items)
    cart_count = cart_items.count()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        items_data = []
        for item in cart_items:
            items_data.append({
                'id': item.id,
                'book_id': item.book.id,
                'title': item.book.title,
                'genre': item.book.genre,
                'price': float(item.book.discount_price or item.book.actual_price),
                'image': item.book.cover_image.url,
                'quantity': item.quantity,
            })
        
        return JsonResponse({
            'success': True,
            'cart_count': cart_count,
            'cart_total': float(total),
            'cart_items': items_data,
        })
    
    return redirect('view_cart')


from django.shortcuts import get_object_or_404, redirect
from .models import Book, Wishlist

def add_to_wishlist(request, id):

    book = get_object_or_404(Book, id=id)

    Wishlist.objects.get_or_create(
        user=request.user,
        book=book
    )

    return redirect(request.META.get('HTTP_REFERER', '/'))


def remove_wishlist(request, id):

    Wishlist.objects.filter(
        user=request.user,
        book_id=id
    ).delete()

    return redirect('/myapp/view_wishlist/')


def view_wishlist(request):

    wishlist = Wishlist.objects.filter(
        user=request.user
    ).select_related('book')

    return render(request, 'user/whishlist.html', {
        'wishlist': wishlist
    })


@login_required
def move_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # Remove from wishlist
    Wishlist.objects.filter(user=request.user, book=book).delete()
    
    # Add to cart
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        book=book,
        defaults={'quantity': 1}
    )
    
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
    
    messages.success(request, f'"{book.title}" moved to your cart!')
    return redirect('/myapp/view_wishlist/')






# ===================== CHECKOUT =====================
@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('book')
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty!')
        return redirect('view_cart')
    
    total = sum(item.subtotal() for item in cart_items)
    addresses = Address.objects.filter(user=request.user)
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_items.count(),
        'addresses': addresses,
    }
    return render(request, 'user/checkout.html', context)


@login_required
@transaction.atomic
@csrf_exempt
def place_order(request):
    if request.method != 'POST':
        return redirect('view_cart')
    
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('book')
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty!')
        return redirect('view_cart')
    
    # Get form data
    fullname = request.POST.get('fullname', '').strip()
    phone = request.POST.get('phone', '').strip()
    address = request.POST.get('address', '').strip()
    city = request.POST.get('city', '').strip()
    state = request.POST.get('state', '').strip()
    pincode = request.POST.get('pincode', '').strip()
    payment_method = request.POST.get('payment_method', 'cod')
    
    # Validate required fields
    if not all([fullname, phone, address, city, state, pincode]):
        messages.error(request, 'Please fill in all required address fields!')
        return redirect('checkout')
    
    # Create or get address
    address_obj, created = Address.objects.get_or_create(
        user=request.user,
        fullname=fullname,
        phone=phone,
        house=address,
        city=city,
        state=state,
        pincode=pincode,
    )
    
    total = sum(item.subtotal() for item in cart_items)
    
    # Create order
    order = Order.objects.create(
        user=request.user,
        address=address_obj,
        total_amount=total,
        status='Pending'
    )
    
    # Create order items and update stock
    for cart_item in cart_items:
        OrderItem.objects.create(
            order=order,
            book=cart_item.book,
            quantity=cart_item.quantity,
            price=cart_item.book.discount_price or cart_item.book.actual_price
        )
        
        # Update stock
        cart_item.book.stock -= cart_item.quantity
        cart_item.book.save()
    
    # Clear cart
    cart_items.delete()
    
    messages.success(request, f'Order #{order.id} placed successfully!')
    return redirect('order_confirmation', order_id=order.id)

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order).select_related('book')
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'user/order_confirmation.html', context)


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'user/my_orders.html', context)


# ===================== RAZORPAY PAYMENT =====================
@login_required
def razorpay_payment(request):
    """Create Razorpay order and redirect to payment page"""
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('book')
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty!')
        return redirect('view_cart')
    
    total = sum(item.subtotal() for item in cart_items)
    amount = float(total) * 100  # Convert to paise
    
    # Get user's address
    address = Address.objects.filter(user=request.user).first()
    
    # Razorpay configuration
    razorpay_api_key = "rzp_live_Su35EVyNYFeKCF"
    razorpay_secret_key = "NQE3JfS6rdlmp8YtHrxF120H"
    
    razorpay_client = razorpay.Client(auth=(razorpay_api_key, razorpay_secret_key))
    
    # Create Razorpay order
    order_data = {
        'amount': int(amount),
        'currency': 'INR',
        'receipt': f'order_{request.user.id}_{int(time.time())}',
        'payment_capture': '1',
    }
    
    razorpay_order = razorpay_client.order.create(data=order_data)
    
    # Save payment record (order is null initially)
    payment = Payment.objects.create(
        order=None,  # Will be updated after order placement
        razorpay_order_id=razorpay_order['id'],
        amount=total,
        status='Pending'
    )
    
    context = {
        'razorpay_api_key': razorpay_api_key,
        'amount': int(amount),
        'currency': 'INR',
        'order_id': razorpay_order['id'],
        'user': request.user,
        'address': address,
        'cart_items': cart_items,
        'total': total,
        'payment_id': payment.id,
    }
    
    return render(request, 'user/payment.html', context)


@login_required
@transaction.atomic
def razorpay_payment_success(request):
    """Handle Razorpay payment success"""
    if request.method != 'POST':
        return redirect('view_cart')
    
    payment_id = request.POST.get('payment_id')
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')
    
    if not all([payment_id, razorpay_payment_id, razorpay_signature]):
        messages.error(request, 'Invalid payment response!')
        return redirect('view_cart')
    
    # Get payment record
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Verify signature
    razorpay_api_key = "rzp_live_Su35EVyNYFeKCF"
    razorpay_secret_key = "NQE3JfS6rdlmp8YtHrxF120H"
    
    razorpay_client = razorpay.Client(auth=(razorpay_api_key, razorpay_secret_key))
    
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        # Verify payment signature
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        # Update payment status
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.status = 'Success'
        payment.save()
        
        # Get cart
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related('book')
        
        if not cart_items:
            messages.warning(request, 'Your cart is empty!')
            return redirect('view_cart')
        
        # Get or create address from POST data
        address, created = Address.objects.get_or_create(
            user=request.user,
            fullname=request.POST.get('fullname', 'Guest'),
            phone=request.POST.get('phone', ''),
            house=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            state=request.POST.get('state', ''),
            pincode=request.POST.get('pincode', ''),
        )
        
        total = sum(item.subtotal() for item in cart_items)
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            address=address,
            total_amount=total,
            status='Paid'
        )
        
        # Create order items and update stock
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                book=cart_item.book,
                quantity=cart_item.quantity,
                price=cart_item.book.discount_price or cart_item.book.actual_price
            )
            
            # Update stock
            cart_item.book.stock -= cart_item.quantity
            cart_item.book.save()
        
        # Update payment with order
        payment.order = order
        payment.save()
        
        # Clear cart
        cart_items.delete()
        
        # Send confirmation emails (optional - comment out if email not configured)
        # send_order_confirmation_emails(order, request.user)
        
        messages.success(request, f'Payment successful! Order #{order.id} placed successfully!')
        return redirect('order_confirmation', order_id=order.id)
        
    except razorpay.errors.SignatureVerificationError:
        payment.status = 'Failed'
        payment.save()
        messages.error(request, 'Payment verification failed! Please try again.')
        return redirect('view_cart')
    except Exception as e:
        payment.status = 'Failed'
        payment.save()
        messages.error(request, f'Payment error: {str(e)}')
        return redirect('view_cart')

def send_order_confirmation_emails(order, user):
    """Send order confirmation emails to customer and admin"""
    try:
        order_items = OrderItem.objects.filter(order=order).select_related('book')
        items_html = ''
        for item in order_items:
            items_html += f'''
                <tr>
                    <td>{item.book.title}</td>
                    <td>{item.quantity}</td>
                    <td>₹{item.price}</td>
                    <td>₹{item.subtotal()}</td>
                </tr>
            '''
        
        # Customer Email
        customer_html = f"""
        <html>
        <body style="font-family: Arial; background:#f4f4f4; padding:30px;">
        <div style="max-width:600px; margin:auto; background:white; border-radius:15px; padding:30px;">
            <h1 style="color:#0b7d45; text-align:center;">Yathisha Books</h1>
            <h2>Thank You For Your Order!</h2>
            <p>Dear <b>{user.username}</b>,</p>
            <p>Your order has been confirmed and payment received.</p>
            <div style="background:#f7fff9; border:1px solid #d4f5dd; padding:20px; border-radius:10px;">
                <h3>📋 Order Details</h3>
                <p><b>Order ID:</b> #{order.id}</p>
                <p><b>Order Date:</b> {order.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                <p><b>Total Amount:</b> ₹{order.total_amount}</p>
                <p><b>Status:</b> {order.status}</p>
            </div>
            <div style="margin-top:20px;">
                <h3>📦 Items Ordered</h3>
                <table style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr style="background:#f0f0f0;">
                            <th style="padding:10px; text-align:left;">Book</th>
                            <th style="padding:10px; text-align:center;">Qty</th>
                            <th style="padding:10px; text-align:right;">Price</th>
                            <th style="padding:10px; text-align:right;">Subtotal</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
            </div>
            <div style="margin-top:20px; padding:15px; background:#f8f8f8; border-radius:10px;">
                <h3>📍 Shipping Address</h3>
                <p>{order.address.fullname}</p>
                <p>{order.address.house}</p>
                <p>{order.address.city}, {order.address.state} - {order.address.pincode}</p>
                <p>Phone: {order.address.phone}</p>
            </div>
            <p style="margin-top:20px;">Thank you for shopping with Yathisha Books!</p>
        </div>
        </body>
        </html>
        """
        
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login("your_email@gmail.com", "your_app_password")  # Replace with your credentials
        
        # Customer email
        customer_msg = MIMEMultipart()
        customer_msg['From'] = "your_email@gmail.com"
        customer_msg['To'] = user.email
        customer_msg['Subject'] = f"Yathisha Books - Order #{order.id} Confirmation"
        customer_msg.attach(MIMEText(customer_html, 'html', 'utf-8'))
        server.sendmail("your_email@gmail.com", user.email, customer_msg.as_string())
        
        server.quit()
        
    except Exception as e:
        print(f"Email error: {str(e)}")