class Solution:
    def rotate(self, nums: list[int], k: int) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """

        while k:
            for i in range(len(nums) - 1, 0, -1):
                nums[i], nums[i - 1] = nums[i - 1], nums[i]


if __name__ == "__main__":
    sol = Solution()
    arr = [1, 2, 3, 4, 5, 6, 7]
    k = 3
    sol.rotate(arr, k)
    print(arr)
