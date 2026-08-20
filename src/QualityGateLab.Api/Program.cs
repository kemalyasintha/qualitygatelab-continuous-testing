using Microsoft.EntityFrameworkCore;
using QualityGateLab.Api.Features.Orders.Persistence;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

var connectionString =
    builder.Configuration.GetConnectionString("OrdersDatabase")
    ?? throw new InvalidOperationException(
        "The OrdersDatabase connection string is missing.");

builder.Services.AddDbContext<OrderDbContext>(options =>
    options.UseSqlite(connectionString));
    
var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();

    app.UseSwaggerUI(options =>
    {
        options.SwaggerEndpoint(
            "/openapi/v1.json",
            "QualityGateLab API v1");
    });
}
app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.Run();
