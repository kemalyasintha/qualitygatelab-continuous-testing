using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using QualityGateLab.Api.Features.Orders.Domain;
using QualityGateLab.Api.Features.Orders.Persistence;

namespace QualityGateLab.IntegrationTests.Orders;

public sealed class OrderPersistenceTests
{
    [Fact]
    public async Task MigrationAndSave_PersistsAndReloadsOrder()
    {
        await using var connection =
            new SqliteConnection("Data Source=:memory:");

        await connection.OpenAsync();

        var options =
            new DbContextOptionsBuilder<OrderDbContext>()
                .UseSqlite(connection)
                .Options;

        Guid orderId;

        await using (var arrangeContext = new OrderDbContext(options))
        {
            var databaseCreated =
            await arrangeContext.Database.EnsureCreatedAsync();

            Assert.True(databaseCreated);

            var order = new Order(
                "customer@example.com",
                "PRODUCT-001",
                2);

            arrangeContext.Orders.Add(order);
            await arrangeContext.SaveChangesAsync();

            orderId = order.Id;
        }

        await using var assertContext = new OrderDbContext(options);

        var savedOrder = await assertContext.Orders
            .SingleAsync(order => order.Id == orderId);

        Assert.Equal(orderId, savedOrder.Id);
        Assert.Equal("customer@example.com", savedOrder.CustomerEmail);
        Assert.Equal("PRODUCT-001", savedOrder.ProductId);
        Assert.Equal(2, savedOrder.Quantity);
        Assert.Equal(OrderStatus.Pending, savedOrder.Status);
        Assert.NotEqual(default, savedOrder.CreatedAtUtc);
    }
}