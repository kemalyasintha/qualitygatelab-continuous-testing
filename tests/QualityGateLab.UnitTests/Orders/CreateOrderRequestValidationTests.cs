using System.ComponentModel.DataAnnotations;
using QualityGateLab.Api.Features.Orders.Contracts;

namespace QualityGateLab.UnitTests.Orders;

public sealed class CreateOrderRequestValidationTests
{
    [Fact]
    public void Validate_WithValidRequest_ReturnsNoErrors()
    {
        var request = CreateValidRequest();

        var results = Validate(request);

        Assert.Empty(results);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("invalid-email")]
    public void Validate_WithInvalidEmail_ReturnsValidationError(
        string? customerEmail)
    {
        var request = new CreateOrderRequest
        {
            CustomerEmail = customerEmail,
            ProductId = "PRODUCT-001",
            Quantity = 1
        };

        var results = Validate(request);

        Assert.Contains(
            results,
            result => result.MemberNames.Contains(
                nameof(CreateOrderRequest.CustomerEmail)));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Validate_WithMissingProductId_ReturnsValidationError(
        string? productId)
    {
        var request = new CreateOrderRequest
        {
            CustomerEmail = "customer@example.com",
            ProductId = productId,
            Quantity = 1
        };

        var results = Validate(request);

        Assert.Contains(
            results,
            result => result.MemberNames.Contains(
                nameof(CreateOrderRequest.ProductId)));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(101)]
    public void Validate_WithQuantityOutsideRange_ReturnsValidationError(
        int quantity)
    {
        var request = new CreateOrderRequest
        {
            CustomerEmail = "customer@example.com",
            ProductId = "PRODUCT-001",
            Quantity = quantity
        };

        var results = Validate(request);

        Assert.Contains(
            results,
            result => result.MemberNames.Contains(
                nameof(CreateOrderRequest.Quantity)));
    }

    [Theory]
    [InlineData(1)]
    [InlineData(100)]
    public void Validate_WithBoundaryQuantity_ReturnsNoErrors(int quantity)
    {
        var request = CreateValidRequest(quantity);

        var results = Validate(request);

        Assert.Empty(results);
    }

    private static CreateOrderRequest CreateValidRequest(int quantity = 1)
    {
        return new CreateOrderRequest
        {
            CustomerEmail = "customer@example.com",
            ProductId = "PRODUCT-001",
            Quantity = quantity
        };
    }

    private static List<ValidationResult> Validate(
        CreateOrderRequest request)
    {
        var results = new List<ValidationResult>();
        var context = new ValidationContext(request);

        Validator.TryValidateObject(
            request,
            context,
            results,
            validateAllProperties: true);

        return results;
    }
}