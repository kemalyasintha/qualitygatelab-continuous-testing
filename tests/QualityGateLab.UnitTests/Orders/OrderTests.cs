using QualityGateLab.Api.Features.Orders.Domain;

namespace QualityGateLab.UnitTests.Orders;

public sealed class OrderTests
{
    [Fact]
    public void Constructor_WithValidInputs_CreatesPendingOrder()
    {
        var order = new Order(
            "customer@example.com",
            "PROD-001",
            2);

        Assert.NotEqual(Guid.Empty, order.Id);
        Assert.Equal("customer@example.com", order.CustomerEmail);
        Assert.Equal("PROD-001", order.ProductId);
        Assert.Equal(2, order.Quantity);
        Assert.Equal(OrderStatus.Pending, order.Status);
        Assert.Equal(TimeSpan.Zero, order.CreatedAtUtc.Offset);
    }

    [Theory]
    [InlineData(1)]
    [InlineData(100)]
    public void Constructor_WithBoundaryQuantity_CreatesOrder(int quantity)
    {
        var order = new Order(
            "customer@example.com",
            "PROD-001",
            quantity);

        Assert.Equal(quantity, order.Quantity);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(101)]
    public void Constructor_WithQuantityOutsideRange_ThrowsException(
        int quantity)
    {
        var exception = Assert.Throws<ArgumentOutOfRangeException>(
            () => new Order(
                "customer@example.com",
                "PROD-001",
                quantity));

        Assert.Equal("quantity", exception.ParamName);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("not-an-email")]
    public void Constructor_WithInvalidEmail_ThrowsException(
        string? customerEmail)
    {
        var exception = Assert.Throws<ArgumentException>(
            () => new Order(
                customerEmail!,
                "PROD-001",
                2));

        Assert.Equal("customerEmail", exception.ParamName);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Constructor_WithMissingProductId_ThrowsException(
        string? productId)
    {
        var exception = Assert.Throws<ArgumentException>(
            () => new Order(
                "customer@example.com",
                productId!,
                2));

        Assert.Equal("productId", exception.ParamName);
    }

    [Fact]
    public void Constructor_CalledTwice_GeneratesUniqueOrderIds()
    {
        var firstOrder = new Order(
            "customer@example.com",
            "PROD-001",
            2);

        var secondOrder = new Order(
            "customer@example.com",
            "PROD-001",
            2);

        Assert.NotEqual(firstOrder.Id, secondOrder.Id);
    }
}
