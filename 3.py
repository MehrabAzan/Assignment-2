def count_ways(numMatrices):
    """
    Return the Catalan number C_{n-1} of full parenthesizations of n matrices.
    Input: numMatrices (n).
    Output: C_{n-1}.
    Locals: catalan, m, total, k.
    """
    if numMatrices <= 1:
        return 1
    catalan = [0] * (numMatrices + 1)
    catalan[0] = 1
    catalan[1] = 1
    for m in range(2, numMatrices + 1):
        total = 0
        for k in range(m):
            total += catalan[k] * catalan[m - 1 - k]
        catalan[m] = total
    return catalan[numMatrices - 1]

def average_work_dp(dims):
    """
    Compute average parenthesization cost via SumCost and N tables.
    Input: dims = [p0, p1, ..., pn] for matrices A1..An.
    Output: (average, sumCost, numWays) for the full chain.
    Locals: numMatrices, numWays, sumCost, length, i, j, ways, total, k,
            leftWays, rightWays, finalMul.
    """
    numMatrices = len(dims) - 1
    numWays = [[0] * (numMatrices + 1) for _ in range(numMatrices + 1)]
    sumCost = [[0] * (numMatrices + 1) for _ in range(numMatrices + 1)]
    for i in range(1, numMatrices + 1):
        numWays[i][i] = 1
        sumCost[i][i] = 0
    for length in range(2, numMatrices + 1):
        for i in range(1, numMatrices - length + 2):
            j = i + length - 1
            ways = 0
            total = 0
            for k in range(i, j):
                leftWays = numWays[i][k]
                rightWays = numWays[k + 1][j]
                ways += leftWays * rightWays
                finalMul = dims[i - 1] * dims[k] * dims[j]
                total += (
                    sumCost[i][k] * rightWays
                    + sumCost[k + 1][j] * leftWays
                    + leftWays * rightWays * finalMul
                )
            numWays[i][j] = ways
            sumCost[i][j] = total
    return (
        sumCost[1][numMatrices] / numWays[1][numMatrices],
        sumCost[1][numMatrices],
        numWays[1][numMatrices],
    )

def all_costs(dims, i, j):
    """
    Recursively list every parenthesization cost of subchain Ai..Aj.
    Input: dims, inclusive indices i and j (1 based matrix indices).
    Output: list of scalar multiplication totals.
    Locals: costs, k, leftCost, rightCost, finalMul.
    """
    if i == j:
        return [0]
    costs = []
    for k in range(i, j):
        for leftCost in all_costs(dims, i, k):
            for rightCost in all_costs(dims, k + 1, j):
                finalMul = dims[i - 1] * dims[k] * dims[j]
                costs.append(leftCost + rightCost + finalMul)
    return costs

def average_work_brute(dims):
    """
    Average parenthesization cost by enumerating every full tree.
    Input: dims = [p0, p1, ..., pn].
    Output: (average, sumCost, numWays).
    Locals: numMatrices, costs.
    """
    numMatrices = len(dims) - 1
    costs = all_costs(dims, 1, numMatrices)
    return sum(costs) / len(costs), sum(costs), len(costs)

def check_instance(dims):
    """
    Assert that DP and brute force agree on one dimension vector.
    Input: dims.
    Output: none (raises on mismatch).
    Locals: avgDp, sumDp, waysDp, avgBrute, sumBrute, waysBrute.
    """
    avgDp, sumDp, waysDp = average_work_dp(dims)
    avgBrute, sumBrute, waysBrute = average_work_brute(dims)
    assert waysDp == waysBrute
    assert sumDp == sumBrute
    assert abs(avgDp - avgBrute) < 1e-9

def main():
    """
    Print the sample average and verify DP against brute force.
    Input: none.
    Output: printed sample and pass message.
    Locals: sampleDims, avgDp, sumDp, waysDp, avgBrute, numMatrices, dims.
    """
    sampleDims = [10, 30, 5, 60]
    avgDp, sumDp, waysDp = average_work_dp(sampleDims)
    avgBrute, _, _ = average_work_brute(sampleDims)
    numMatrices = len(sampleDims) - 1
    print("dims", sampleDims)
    print(
        "num ways",
        waysDp,
        "(Catalan C_" + str(numMatrices - 1) + " =",
        count_ways(numMatrices),
        ")",
    )
    print("sum of costs DP", sumDp)
    print("average work DP", avgDp)
    print("average work brute", avgBrute)
    assert waysDp == count_ways(numMatrices)
    assert abs(avgDp - avgBrute) < 1e-9
    assert abs(avgDp - 15750.0) < 1e-9
    for dims in ([2, 3, 4], [5, 10, 3, 12], [2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6]):
        check_instance(dims)
    print("all tests passed")

if __name__ == "__main__":
    main()