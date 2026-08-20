using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using QualityGateLab.Api.Features.Orders.Contracts;
using QualityGateLab.Api.Features.Orders.Domain;
using QualityGateLab.Api.Features.Orders.Persistence;

namespace QualityGateLab.Api.Features.Orders.Controllers;

[ApiController]
[Route("api/orders")]
public sealed class OrdersController(OrderDbContext dbContext)
    : ControllerBase
{
    [HttpPost]
    [ProducesResponseType(
        typeof(OrderResponse),
        StatusCodes.Status201Created)]
    [ProducesResponseType(
        typeof(ValidationProblemDetails),
        StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<OrderResponse>> Create(
        CreateOrderRequest request,
        CancellationToken cancellationToken)
    {
        var order = new Order(
            request.CustomerEmail!,
            request.ProductId!,
            request.Quantity);

        dbContext.Orders.Add(order);

        await dbContext.SaveChangesAsync(cancellationToken);

        var response = OrderResponse.FromDomain(order);

        return CreatedAtAction(
            nameof(GetById),
            new { id = order.Id },
            response);
    }

    [HttpGet("{id:guid}")]
    [ProducesResponseType(
        typeof(OrderResponse),
        StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<OrderResponse>> GetById(
        Guid id,
        CancellationToken cancellationToken)
    {
        var order = await dbContext.Orders
            .AsNoTracking()
            .SingleOrDefaultAsync(
                current => current.Id == id,
                cancellationToken);

        if (order is null)
        {
            return NotFound();
        }

        return Ok(OrderResponse.FromDomain(order));
    }
}