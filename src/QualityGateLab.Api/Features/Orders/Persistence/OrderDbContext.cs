using Microsoft.EntityFrameworkCore;
using QualityGateLab.Api.Features.Orders.Domain;

namespace QualityGateLab.Api.Features.Orders.Persistence;

public sealed class OrderDbContext(
    DbContextOptions<OrderDbContext> options)
    : DbContext(options)
{
    public DbSet<Order> Orders => Set<Order>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        var order = modelBuilder.Entity<Order>();

        order.ToTable("Orders", table =>
        {
            table.HasCheckConstraint(
                "CK_Orders_Quantity",
                "\"Quantity\" BETWEEN 1 AND 100");
        });

        order.HasKey(current => current.Id);

        order.Property(current => current.CustomerEmail)
            .IsRequired()
            .HasMaxLength(254);

        order.Property(current => current.ProductId)
            .IsRequired()
            .HasMaxLength(100);

        order.Property(current => current.Quantity)
            .IsRequired();

        order.Property(current => current.Status)
            .HasConversion<string>()
            .IsRequired()
            .HasMaxLength(20);

        order.Property(current => current.CreatedAtUtc)
            .IsRequired();
    }
}