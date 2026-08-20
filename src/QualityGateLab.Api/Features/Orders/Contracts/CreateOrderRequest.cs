using System.ComponentModel.DataAnnotations;

namespace QualityGateLab.Api.Features.Orders.Contracts;

public sealed class CreateOrderRequest
{
    [Required]
    [EmailAddress]
    public string? CustomerEmail { get; init; }

    [Required]
    public string? ProductId { get; init; }

    [Range(1, 100)]
    public int Quantity { get; init; }
}