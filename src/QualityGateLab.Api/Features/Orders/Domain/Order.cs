using System.Net.Mail;

namespace QualityGateLab.Api.Features.Orders.Domain;

public sealed class Order
{
    private Order()
    {
        CustomerEmail = string.Empty;
        ProductId = string.Empty;
    }

    public Order(
        string customerEmail,
        string productId,
        int quantity,
        TimeProvider? timeProvider = null)
    {
        var normalizedEmail = customerEmail?.Trim();

        if (string.IsNullOrWhiteSpace(normalizedEmail) ||
            !MailAddress.TryCreate(normalizedEmail, out _))
        {
            throw new ArgumentException(
                "A valid customer email is required.",
                nameof(customerEmail));
        }

        if (string.IsNullOrWhiteSpace(productId))
        {
            throw new ArgumentException(
                "Product ID is required.",
                nameof(productId));
        }

        if (quantity is < 1 or > 100)
        {
            throw new ArgumentOutOfRangeException(
                nameof(quantity),
                quantity,
                "Quantity must be between 1 and 100.");
        }

        Id = Guid.NewGuid();
        CustomerEmail = normalizedEmail;
        ProductId = productId.Trim();
        Quantity = quantity;
        Status = OrderStatus.Pending;
        CreatedAtUtc = (timeProvider ?? TimeProvider.System).GetUtcNow();
    }

    public Guid Id { get; private set; }

    public string CustomerEmail { get; private set; }

    public string ProductId { get; private set; }

    public int Quantity { get; private set; }

    public OrderStatus Status { get; private set; }

    public DateTimeOffset CreatedAtUtc { get; private set; }
}