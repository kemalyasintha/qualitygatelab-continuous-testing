using System.Data.Common;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using QualityGateLab.Api.Features.Orders.Persistence;

namespace QualityGateLab.IntegrationTests.Infrastructure;

public sealed class QualityGateLabApiFactory
    : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(
        IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");

        builder.ConfigureServices(services =>
        {
            services.RemoveAll<OrderDbContext>();
            services.RemoveAll<DbContextOptions<OrderDbContext>>();

            services.AddSingleton<DbConnection>(_ =>
            {
                var connection =
                    new SqliteConnection("Data Source=:memory:");

                connection.Open();

                return connection;
            });

            services.AddDbContext<OrderDbContext>(
                (serviceProvider, options) =>
                {
                    var connection =
                        serviceProvider.GetRequiredService<DbConnection>();

                    options.UseSqlite(connection);
                });
        });
    }

    public async Task ResetDatabaseAsync()
    {
        using var scope = Services.CreateScope();

        var dbContext =
            scope.ServiceProvider.GetRequiredService<OrderDbContext>();

        await dbContext.Database.EnsureDeletedAsync();
        await dbContext.Database.EnsureCreatedAsync();
    }
}