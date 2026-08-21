using System.Net;
using System.Net.Http.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using QualityGateLab.Api.Features.Orders.Contracts;
using QualityGateLab.Api.Features.Orders.Persistence;
using QualityGateLab.IntegrationTests.Infrastructure;

namespace QualityGateLab.IntegrationTests.Orders;

public sealed class CreateOrderApiTests(
    QualityGateLabApiFactory factory)
    : IClassFixture<QualityGateLabApiFactory>
{
    [Fact]
    public async Task PostValidOrder_Returns201AndPersistsOrder()
    {
        await factory.ResetDatabaseAsync();

        using var client = factory.CreateClient();

        var request = new CreateOrderRequest
        {
            CustomerEmail = "customer@example.com",
            ProductId = "PRODUCT-001",
            Quantity = 2
        };

        var response = await client.PostAsJsonAsync(
            "/api/orders",
            request);

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.NotNull(response.Headers.Location);

        var createdOrder =
            await response.Content.ReadFromJsonAsync<OrderResponse>();

        Assert.NotNull(createdOrder);
        Assert.NotEqual(Guid.Empty, createdOrder.Id);
        Assert.Equal(request.CustomerEmail, createdOrder.CustomerEmail);
        Assert.Equal(request.ProductId, createdOrder.ProductId);
        Assert.Equal(request.Quantity, createdOrder.Quantity);
        Assert.Equal("Pending", createdOrder.Status);

        using var scope = factory.Services.CreateScope();

        var dbContext =
            scope.ServiceProvider.GetRequiredService<OrderDbContext>();

        var persistedOrder = await dbContext.Orders
            .AsNoTracking()
            .SingleAsync(order => order.Id == createdOrder.Id);

        Assert.Equal(createdOrder.Id, persistedOrder.Id);
    }

    [Fact]
    public async Task GetCreatedOrder_ReturnsPersistedOrder()
    {
        await factory.ResetDatabaseAsync();

        using var client = factory.CreateClient();

        var request = new CreateOrderRequest
        {
            CustomerEmail = "customer@example.com",
            ProductId = "PRODUCT-001",
            Quantity = 2
        };

        var postResponse = await client.PostAsJsonAsync(
            "/api/orders",
            request);

        Assert.Equal(HttpStatusCode.Created, postResponse.StatusCode);
        Assert.NotNull(postResponse.Headers.Location);

        var getResponse = await client.GetAsync(
            postResponse.Headers.Location);

        Assert.Equal(HttpStatusCode.OK, getResponse.StatusCode);

        var retrievedOrder =
            await getResponse.Content.ReadFromJsonAsync<OrderResponse>();

        Assert.NotNull(retrievedOrder);
        Assert.Equal(request.CustomerEmail, retrievedOrder.CustomerEmail);
        Assert.Equal("Pending", retrievedOrder.Status);
    }

    [Fact]
    public async Task GetMissingOrder_Returns404()
    {
        await factory.ResetDatabaseAsync();

        using var client = factory.CreateClient();

        var response = await client.GetAsync(
            $"/api/orders/{Guid.NewGuid()}");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Theory]
    [InlineData("invalid-email", "PRODUCT-001", 1)]
    [InlineData("customer@example.com", "", 1)]
    [InlineData("customer@example.com", "PRODUCT-001", 0)]
    [InlineData("customer@example.com", "PRODUCT-001", 101)]
    public async Task PostInvalidOrder_Returns400AndDoesNotPersist(
        string customerEmail,
        string productId,
        int quantity)
    {
        await factory.ResetDatabaseAsync();

        using var client = factory.CreateClient();

        var request = new CreateOrderRequest
        {
            CustomerEmail = customerEmail,
            ProductId = productId,
            Quantity = quantity
        };

        var response = await client.PostAsJsonAsync(
            "/api/orders",
            request);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);

        using var scope = factory.Services.CreateScope();

        var dbContext =
            scope.ServiceProvider.GetRequiredService<OrderDbContext>();

        Assert.Equal(0, await dbContext.Orders.CountAsync());
    }
}
