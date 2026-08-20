using QualityGateLab.Api.Features.Orders.Domain;

namespace QualityGateLab.Api.Features.Orders.Contracts;

public sealed record OrderResponse(
    Guid Id,
    string CustomerEmail,
    string ProductId,
    int Quantity,
    string Status,
    DateTimeOffset CreatedAtUtc)
{
    public static OrderResponse FromDomain(Order order)
    {
        return new OrderResponse(
            order.Id,
            order.CustomerEmail,
            order.ProductId,
            order.Quantity,
            order.Status.ToString(),
            order.CreatedAtUtc);
    }
}